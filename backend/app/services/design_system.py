"""
Design System Module
Provides design guidelines and templates for different styles and business types
"""

class DesignSystem:
    """Design system with style guidelines and templates"""
    
    def get_design_system_prompt(self, style: str) -> str:
        """Get design system prompt for specific style"""
        return ""
    
    def get_component_architecture_prompt(self, style: str) -> str:
        """Get component architecture guidelines"""
        return ""
    
    def get_quality_checklist(self) -> str:
        """Get quality checklist"""
        return """

## QUALITY CHECKLIST
Before completing generation, verify:
✓ All sections present and complete
✓ Mobile responsive (test at 375px, 768px, 1024px)
✓ No broken HTML tags
✓ CSS properly scoped and organized
✓ JavaScript functions working
✓ WhatsApp integration functional (if requested)
✓ Contact form with validation
✓ Smooth scrolling between sections
✓ Professional visual hierarchy
✓ Consistent color palette throughout
"""
    
    def get_business_template_prompt(self, business_type: str) -> str:
        """Get business-specific template guidelines"""
        
        templates = {
            "restaurant": """
### RESTAURANT TEMPLATE
**Required Sections:**
- Menu section with food items, prices, descriptions
- Photo gallery of dishes
- Opening hours prominently displayed
- Table reservation/WhatsApp booking CTA
- Location with maps
- Dietary information (Halal, Vegetarian options)

**Design Elements:**
- Warm, appetizing color scheme
- High-quality food photography placeholders
- Menu organized by categories (Starters, Mains, Desserts, Drinks)
- Price format: RM XX.XX
- WhatsApp "Order Now" buttons
""",
            
            "cafe": """
### CAFE TEMPLATE
**Required Sections:**
- Beverage menu with prices
- Ambiance/atmosphere photos
- Opening hours
- WiFi availability mention
- Instagram-worthy photo spots mention
- Location and parking info

**Design Elements:**
- Modern, Instagram-friendly aesthetic
- Bright, airy color scheme
- Emphasis on coffee/beverages
- Social media integration
""",
            
            "salon": """
### SALON/BEAUTY TEMPLATE
**Required Sections:**
- Services list with prices and duration
- Stylist/team profiles
- Before/After gallery
- Booking system (WhatsApp)
- Operating hours
- Price list clearly displayed

**Design Elements:**
- Elegant, sophisticated design
- Soft color palette
- Professional photography
- Trust-building elements
""",
            
            "retail": """
### RETAIL SHOP TEMPLATE
**Required Sections:**
- Product catalog/grid
- Shopping cart functionality
- WhatsApp ordering
- Product categories
- Special offers/promotions
- Store location and hours

**Design Elements:**
- E-commerce focused
- Clear product cards
- Shopping cart UI
- Call-to-action buttons
"""
        }
        
        return templates.get(business_type.lower(), "")

# Create singleton instance
design_system = DesignSystem()