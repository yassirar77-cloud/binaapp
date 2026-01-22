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

        logger.info(f"ToyyibPay service initialized (sandbox: {self.sandbox})")

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
            # Convert amount to cents (ToyyibPay expects amount in cents)
            amount_in_cents = int(bill_amount * 100)

            data = {
                'userSecretKey': self.secret_key,
                'categoryCode': self.category_code,
                'billName': bill_name,
                'billDescription': bill_description,
                'billPriceSetting': 1,  # Fixed price
                'billPayorInfo': 1,  # Require payer info
                'billAmount': amount_in_cents,
                'billReturnUrl': self.return_url,
                'billCallbackUrl': self.callback_url,
                'billExternalReferenceNo': bill_external_reference_no or '',
                'billTo': bill_name_customer,
                'billEmail': bill_email,
                'billPhone': bill_phone,
                'billSplitPayment': 0,
                'billSplitPaymentArgs': '',
                'billPaymentChannel': 0,  # FPX only
                'billContentEmail': f'Thank you for your payment for {bill_name}',
                'billChargeToCustomer': 1,  # Charge payment fee to customer
            }

            response = requests.post(
                f"{self.base_url}/index.php/api/createBill",
                data=data,
                timeout=30
            )

            response.raise_for_status()
            result = response.json()

            if isinstance(result, list) and len(result) > 0:
                bill_code = result[0].get('BillCode')
                if bill_code:
                    payment_url = f"{self.base_url}/{bill_code}"
                    logger.info(f"Bill created successfully: {bill_code}")
                    return {
                        'success': True,
                        'bill_code': bill_code,
                        'payment_url': payment_url
                    }

            logger.error(f"Failed to create bill: {result}")
            return {
                'success': False,
                'error': 'Failed to create bill',
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
            Dict with test result
        """
        try:
            # Create a test bill with minimal amount
            result = self.create_bill(
                bill_name="BinaApp Test Bill",
                bill_description="Test connection to ToyyibPay",
                bill_amount=1.00,  # RM 1.00 test
                bill_email="test@binaapp.my",
                bill_phone="0123456789",
                bill_name_customer="Test Customer",
                bill_external_reference_no="TEST_CONNECTION"
            )

            return result

        except Exception as e:
            logger.error(f"ToyyibPay connection test failed: {e}")
            return {
                'success': False,
                'error': str(e)
            }


# Create singleton instance
toyyibpay_service = ToyyibPayService()
