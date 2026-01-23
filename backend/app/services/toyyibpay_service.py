"""
ToyyibPay Service - Malaysian Payment Gateway Integration
Handles bill creation and payment processing
"""

import requests
from typing import Dict, Optional
from loguru import logger

from app.core.config import settings


class ToyyibPayService:
    """Service for ToyyibPay payment operations"""

    def __init__(self):
        self.secret_key = settings.TOYYIBPAY_SECRET_KEY
        self.category_code = settings.TOYYIBPAY_CATEGORY_CODE
        self.sandbox = settings.TOYYIBPAY_SANDBOX
        self.callback_url = settings.TOYYIBPAY_CALLBACK_URL
        self.return_url = settings.TOYYIBPAY_RETURN_URL

        # Set base URL based on sandbox mode
        if self.sandbox:
            self.base_url = "https://dev.toyyibpay.com"
        else:
            self.base_url = "https://toyyibpay.com"

        # Warn if configuration is missing
        if not self.secret_key:
            logger.warning("TOYYIBPAY_SECRET_KEY is not set! Payment features will not work.")
        if not self.category_code:
            logger.warning("TOYYIBPAY_CATEGORY_CODE is not set! Payment features will not work.")

        logger.info(f"ToyyibPay service initialized (sandbox: {self.sandbox}, configured: {bool(self.secret_key and self.category_code)})")

    def _format_phone(self, phone: str) -> str:
        """
        Format phone number for ToyyibPay
        ToyyibPay requires: 60123456789 (no spaces, no dashes, starts with 60)
        """
        if not phone:
            return '60123456789'  # Default fallback phone

        # Remove all non-digit characters
        phone = ''.join(filter(str.isdigit, phone))

        if not phone:
            return '60123456789'  # Default fallback phone

        # Ensure it starts with 60 (Malaysia code)
        if not phone.startswith('60'):
            if phone.startswith('0'):
                phone = '60' + phone[1:]  # 0123456789 -> 60123456789
            else:
                phone = '60' + phone  # 123456789 -> 60123456789

        # Validate length (should be 11-12 digits: 60 + 9-10 digit number)
        if len(phone) < 11 or len(phone) > 13:
            logger.warning(f"Invalid phone length after formatting: {phone}")
            return '60123456789'  # Fallback to default

        return phone

    def _clean_name(self, name: str) -> str:
        """Clean customer name for ToyyibPay - remove special characters"""
        if not name:
            return 'Customer'
        # Keep only alphanumeric and spaces
        cleaned = ''.join(c for c in name if c.isalnum() or c.isspace())
        # Limit length to 100 chars
        cleaned = cleaned[:100].strip()
        return cleaned if cleaned else 'Customer'

    def create_bill(
        self,
        bill_name: str,
        bill_description: str,
        bill_amount: float,  # Amount in RM (e.g., 29.00)
        bill_email: str,
        bill_phone: str,
        bill_name_customer: str,
        bill_external_reference_no: Optional[str] = None,
    ) -> Dict:
        """
        Create a bill in ToyyibPay

        Args:
            bill_name: Name of the bill
            bill_description: Description of the bill
            bill_amount: Amount in RM (will be converted to cents)
            bill_email: Customer email
            bill_phone: Customer phone number
            bill_name_customer: Customer name
            bill_external_reference_no: Optional external reference number

        Returns:
            Dict with bill_code and payment_url on success
        """
        try:
            # Validate required configuration
            if not self.secret_key:
                logger.error("ToyyibPay secret key is not configured. Set TOYYIBPAY_SECRET_KEY environment variable.")
                return {
                    'success': False,
                    'error': 'Payment gateway not configured. Please contact support.'
                }

            if not self.category_code:
                logger.error("ToyyibPay category code is not configured. Set TOYYIBPAY_CATEGORY_CODE environment variable.")
                return {
                    'success': False,
                    'error': 'Payment gateway not configured. Please contact support.'
                }

            # Format and validate inputs
            formatted_phone = self._format_phone(bill_phone)
            cleaned_name = self._clean_name(bill_name_customer)
            cleaned_bill_name = bill_name[:30] if bill_name else 'BinaApp Payment'  # Max 30 chars
            cleaned_description = bill_description[:100] if bill_description else 'Payment'  # Max 100 chars

            # Validate amount
            if bill_amount <= 0:
                logger.error(f"Invalid bill amount: {bill_amount}")
                return {
                    'success': False,
                    'error': 'Amount must be positive'
                }

            # Convert amount to cents (ToyyibPay expects amount in cents)
            amount_in_cents = int(bill_amount * 100)

            logger.info(f"📤 Creating ToyyibPay bill:")
            logger.info(f"   Bill Name: {cleaned_bill_name}")
            logger.info(f"   Amount: RM{bill_amount} ({amount_in_cents} cents)")
            logger.info(f"   Email: {bill_email}")
            logger.info(f"   Phone: {formatted_phone}")
            logger.info(f"   Customer: {cleaned_name}")
            logger.info(f"   Ref: {bill_external_reference_no}")

            data = {
                'userSecretKey': self.secret_key,
                'categoryCode': self.category_code,
                'billName': cleaned_bill_name,
                'billDescription': cleaned_description,
                'billPriceSetting': 1,  # Fixed price
                'billPayorInfo': 1,  # Require payer info
                'billAmount': amount_in_cents,
                'billReturnUrl': self.return_url or '',
                'billCallbackUrl': self.callback_url or '',
                'billExternalReferenceNo': bill_external_reference_no or '',
                'billTo': cleaned_name,
                'billEmail': bill_email,
                'billPhone': formatted_phone,
                'billSplitPayment': 0,
                'billSplitPaymentArgs': '',
                'billPaymentChannel': '0',  # FPX only (string)
                'billContentEmail': f'Terima kasih atas pembayaran untuk {cleaned_bill_name}',
                'billChargeToCustomer': 1,  # Charge payment fee to customer
                'billExpiryDate': '',
                'billExpiryDays': 3,
            }

            logger.info(f"📤 Sending request to: {self.base_url}/index.php/api/createBill")

            response = requests.post(
                f"{self.base_url}/index.php/api/createBill",
                data=data,
                timeout=30
            )

            logger.info(f"📥 Response status: {response.status_code}")
            logger.info(f"📥 Response body: {response.text[:500]}")  # Limit log length

            # Don't raise for 400 errors - we want to parse the response
            if response.status_code >= 500:
                response.raise_for_status()

            result = response.json()

            # Parse ToyyibPay response
            if isinstance(result, list) and len(result) > 0:
                bill_code = result[0].get('BillCode')
                if bill_code:
                    payment_url = f"{self.base_url}/{bill_code}"
                    logger.info(f"✅ Bill created successfully: {bill_code}")
                    logger.info(f"✅ Payment URL: {payment_url}")
                    return {
                        'success': True,
                        'bill_code': bill_code,
                        'payment_url': payment_url
                    }

            # Handle error responses from ToyyibPay
            error_message = 'Failed to create bill'
            if isinstance(result, list) and len(result) > 0:
                # ToyyibPay sometimes returns error messages in the array
                first_item = result[0]
                if isinstance(first_item, dict):
                    error_message = first_item.get('msg', first_item.get('message', str(first_item)))
                else:
                    error_message = str(first_item)
            elif isinstance(result, dict):
                error_message = result.get('msg', result.get('message', result.get('error', str(result))))

            logger.error(f"❌ ToyyibPay bill creation failed: {error_message}")
            logger.error(f"❌ Full response: {result}")
            return {
                'success': False,
                'error': error_message,
                'details': result
            }

        except requests.exceptions.RequestException as e:
            logger.error(f"ToyyibPay API request failed: {e}")
            return {
                'success': False,
                'error': 'API request failed',
                'details': str(e)
            }
        except Exception as e:
            logger.error(f"Error creating ToyyibPay bill: {e}")
            return {
                'success': False,
                'error': str(e)
            }

    def verify_callback(self, data: Dict) -> Dict:
        """
        Verify and process callback from ToyyibPay

        Args:
            data: Callback data from ToyyibPay

        Returns:
            Dict with verification result
        """
        try:
            bill_code = data.get('billcode')
            status = data.get('status')
            order_id = data.get('order_id')
            amount = data.get('amount')
            transaction_id = data.get('transaction_id')
            ref_no = data.get('refno')

            logger.info(f"ToyyibPay callback: bill={bill_code}, status={status}, ref={ref_no}")

            # Status codes:
            # 1 = Success
            # 2 = Pending
            # 3 = Failed

            if status == '1':
                return {
                    'success': True,
                    'status': 'paid',
                    'bill_code': bill_code,
                    'transaction_id': transaction_id,
                    'reference': ref_no,
                    'amount': amount
                }
            elif status == '2':
                return {
                    'success': True,
                    'status': 'pending',
                    'bill_code': bill_code
                }
            else:
                return {
                    'success': False,
                    'status': 'failed',
                    'bill_code': bill_code
                }

        except Exception as e:
            logger.error(f"Error verifying ToyyibPay callback: {e}")
            return {
                'success': False,
                'error': str(e)
            }

    def get_bill_transactions(self, bill_code: str) -> Dict:
        """
        Get transactions for a bill

        Args:
            bill_code: The bill code to check

        Returns:
            Dict with transaction details
        """
        try:
            data = {
                'userSecretKey': self.secret_key,
                'billCode': bill_code
            }

            response = requests.post(
                f"{self.base_url}/index.php/api/getBillTransactions",
                data=data,
                timeout=30
            )

            response.raise_for_status()
            result = response.json()

            return {
                'success': True,
                'transactions': result
            }

        except Exception as e:
            logger.error(f"Error getting bill transactions: {e}")
            return {
                'success': False,
                'error': str(e)
            }

    def test_connection(self) -> Dict:
        """
        Test connection to ToyyibPay API by creating a test bill

        Returns:
            Dict with test result including configuration details
        """
        import time
        timestamp = int(time.time())

        try:
            logger.info("🔧 Testing ToyyibPay connection...")

            # Configuration details (mask secret key)
            config_info = {
                'sandbox': self.sandbox,
                'base_url': self.base_url,
                'secret_key_present': bool(self.secret_key),
                'secret_key_length': len(self.secret_key) if self.secret_key else 0,
                'secret_key_preview': f"{self.secret_key[:8]}..." if self.secret_key and len(self.secret_key) > 8 else 'NOT SET',
                'category_code': self.category_code or 'NOT SET',
                'callback_url': self.callback_url or 'NOT SET',
                'return_url': self.return_url or 'NOT SET',
            }

            logger.info(f"🔧 Configuration: {config_info}")

            # Check configuration first
            if not self.secret_key or not self.category_code:
                return {
                    'success': False,
                    'error': 'ToyyibPay not configured. Missing TOYYIBPAY_SECRET_KEY or TOYYIBPAY_CATEGORY_CODE.',
                    'configured': False,
                    'config': config_info
                }

            # Create a test bill with minimal amount
            result = self.create_bill(
                bill_name="BinaApp Test",
                bill_description="Test connection to ToyyibPay",
                bill_amount=1.00,  # RM 1.00 test
                bill_email="test@binaapp.my",
                bill_phone="60123456789",
                bill_name_customer="Test Customer",
                bill_external_reference_no=f"TEST_{timestamp}"
            )

            # Add config info to result
            result['config'] = config_info
            return result

        except Exception as e:
            logger.error(f"ToyyibPay connection test failed: {e}", exc_info=True)
            return {
                'success': False,
                'error': str(e),
                'config': {
                    'sandbox': self.sandbox,
                    'base_url': self.base_url,
                    'secret_key_present': bool(self.secret_key),
                    'category_code': self.category_code or 'NOT SET',
                }
            }


# Create singleton instance
toyyibpay_service = ToyyibPayService()
