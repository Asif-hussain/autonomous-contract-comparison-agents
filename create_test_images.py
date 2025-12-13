"""
Script to Generate Sample Contract Images for Testing

This script creates simple contract images from text templates.
Run this to generate test images if you don't have actual contract scans.

Usage:
    python create_test_images.py
"""

from PIL import Image, ImageDraw, ImageFont
import os


def create_contract_image(text: str, filename: str, width: int = 800, height: int = 1000):
    """
    Create a simple contract image from text.

    Args:
        text: Contract text content
        filename: Output filename (e.g., 'contract1_original.jpg')
        width: Image width in pixels
        height: Image height in pixels
    """
    # Create white background
    image = Image.new('RGB', (width, height), color='white')
    draw = ImageDraw.Draw(image)

    # Try to use a default font, fall back to default if not available
    try:
        # Try to use a common system font
        font_title = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 24)
        font_body = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 16)
    except:
        try:
            # Try alternative font paths
            font_title = ImageFont.truetype("/Library/Fonts/Arial.ttf", 24)
            font_body = ImageFont.truetype("/Library/Fonts/Arial.ttf", 16)
        except:
            # Use default font
            font_title = ImageFont.load_default()
            font_body = ImageFont.load_default()

    # Draw text on image
    y_position = 50
    line_height = 25

    for line in text.split('\n'):
        if line.strip():
            # Use larger font for headers (all caps or starts with SECTION)
            if line.isupper() or line.startswith('SECTION') or line.startswith('EXHIBIT'):
                draw.text((50, y_position), line, fill='black', font=font_title)
                y_position += 35
            else:
                draw.text((50, y_position), line, fill='black', font=font_body)
                y_position += line_height
        else:
            y_position += 15  # Extra space for blank lines

    # Save image
    image.save(filename, 'JPEG', quality=95)
    print(f"✓ Created: {filename}")


# Contract 1: Original
CONTRACT1_ORIGINAL = """
SERVICE AGREEMENT

This Service Agreement ("Agreement") is entered into as of January 1, 2024
between CLIENT CORPORATION ("Client") and SERVICE PROVIDER INC ("Vendor").

SECTION 1.0 - DEFINITIONS
1.1 "Services" means the professional consulting services described in Exhibit A
1.2 "Term" means the period specified in Section 3.0

SECTION 2.0 - PAYMENT TERMS
2.1 Payment Schedule: Client shall pay Vendor within 30 days of invoice receipt
2.2 Payment Method: All payments shall be made via wire transfer or check
2.3 Late Fees: Payments not received within 30 days shall incur 1.5% monthly interest

SECTION 3.0 - TERM AND TERMINATION
3.1 Initial Term: This Agreement shall commence on January 1, 2024 and continue
    for a period of 12 months
3.2 Termination for Convenience: Either party may terminate upon 30 days written notice

SECTION 4.0 - CONFIDENTIALITY
4.1 Confidential Information: Both parties shall maintain confidentiality of all
    proprietary information disclosed during the term
4.2 Duration: Confidentiality obligations shall survive for 2 years after termination

SECTION 5.0 - LIMITATION OF LIABILITY
5.1 Neither party shall be liable for indirect, incidental, or consequential damages

EXHIBIT A - SERVICE DESCRIPTION
Vendor shall provide professional consulting services on a time and materials basis.
Services include strategic planning, process optimization, and technology advisory.
"""

# Contract 1: Amendment
CONTRACT1_AMENDMENT = """
AMENDMENT NO. 1 TO SERVICE AGREEMENT

This Amendment is entered into as of June 1, 2024 between CLIENT CORPORATION
and SERVICE PROVIDER INC.

WHEREAS, the parties entered into a Service Agreement dated January 1, 2024;
WHEREAS, the parties wish to modify certain terms;

NOW THEREFORE, the Agreement is amended as follows:

SECTION 1.0 - DEFINITIONS
(No changes)

SECTION 2.0 - PAYMENT TERMS
2.1 Payment Schedule: Client shall pay Vendor within 45 days of invoice receipt.
    Early Payment Discount: Client shall receive a 2% discount for payments
    received within 15 days of invoice date.
2.2 Payment Method: All payments shall be made via wire transfer or check
2.3 Late Fees: Payments not received within 45 days shall incur 1.5% monthly interest

SECTION 3.0 - TERM AND TERMINATION
(No changes)

SECTION 4.0 - CONFIDENTIALITY
4.1 Confidential Information: Both parties shall maintain confidentiality of all
    proprietary information disclosed during the term
4.2 Duration: Confidentiality obligations shall survive for 5 years after termination

SECTION 5.0 - LIMITATION OF LIABILITY
(No changes)

EXHIBIT A - SERVICE DESCRIPTION
Vendor shall provide professional consulting services on a time and materials basis.
Services include strategic planning, process optimization, and technology advisory.

Service Level Agreement:
- Vendor guarantees 99.9% uptime for all technology systems
- Downtime exceeding 0.1% shall result in service credits of $1,000 per hour
- Response time for critical issues: 2 hours
"""

# Contract 2: Original
CONTRACT2_ORIGINAL = """
SOFTWARE LICENSE AGREEMENT

Effective Date: March 1, 2024
Between: TECH SOLUTIONS INC ("Licensor") and BUSINESS CORP ("Licensee")

SECTION 1.0 - GRANT OF LICENSE
1.1 Licensor grants Licensee a non-exclusive, non-transferable license to use
    the Software as defined herein
1.2 License Type: Enterprise license for up to 100 named users

SECTION 2.0 - RESTRICTIONS
2.1 Licensee shall not reverse engineer, decompile, or disassemble the Software
2.2 All intellectual property rights remain with Licensor

SECTION 3.0 - FEES AND PAYMENT
3.1 License Fee: Licensee shall pay an annual license fee of $50,000
3.2 Payment Terms: Annual fee due within 30 days of invoice

SECTION 4.0 - MAINTENANCE AND SUPPORT
4.1 Licensor shall provide software updates and bug fixes
4.2 Email support available during business hours (9 AM - 5 PM EST, Mon-Fri)
4.3 Response time: 24-48 hours for non-critical issues

SECTION 5.0 - TERM
5.1 Initial Term: 12 months from Effective Date
5.2 Renewal: Automatically renews for successive 12-month periods unless either
    party provides 60 days written notice of non-renewal

SECTION 6.0 - WARRANTIES
6.1 Licensor warrants the Software will perform substantially as described
6.2 Warranty Period: 90 days from delivery

SECTION 7.0 - LIMITATION OF LIABILITY
7.1 Maximum liability: Fees paid in preceding 12 months
"""

# Contract 2: Amendment
CONTRACT2_AMENDMENT = """
FIRST AMENDMENT TO SOFTWARE LICENSE AGREEMENT

Amendment Date: September 1, 2024
Original Agreement Date: March 1, 2024

The parties agree to amend the Software License Agreement as follows:

SECTION 1.0 - GRANT OF LICENSE
(No changes)

SECTION 2.0 - RESTRICTIONS
(No changes)

SECTION 3.0 - FEES AND PAYMENT
3.1 License Fee: Licensee shall pay an annual license fee of $60,000
3.2 Payment Terms: Annual fee due within 30 days of invoice, OR Licensee may
    elect quarterly payments of $15,500 due on the first day of each quarter

SECTION 4.0 - MAINTENANCE AND SUPPORT
4.1 Licensor shall provide software updates and bug fixes
4.2 Premium 24/7 support available via phone, email, and online portal
4.3 Response time: 2 hours for critical issues, 8 hours for standard issues

SECTION 5.0 - TERM
5.1 Initial Term: 24 months from Effective Date
5.2 Renewal: Automatically renews for successive 6-month periods unless either
    party provides 60 days written notice of non-renewal

SECTION 6.0 - WARRANTIES
(No changes)

SECTION 7.0 - LIMITATION OF LIABILITY
(No changes)

All other terms and conditions of the original Agreement remain in full force.
"""


def main():
    """Generate all test contract images."""

    # Create output directory if it doesn't exist
    output_dir = "data/test_contracts"
    os.makedirs(output_dir, exist_ok=True)

    print("\n" + "="*60)
    print("GENERATING TEST CONTRACT IMAGES")
    print("="*60 + "\n")

    # Generate Contract 1 images
    print("Contract Pair 1: Service Agreement")
    create_contract_image(
        CONTRACT1_ORIGINAL,
        f"{output_dir}/contract1_original.jpg",
        width=900,
        height=1200
    )
    create_contract_image(
        CONTRACT1_AMENDMENT,
        f"{output_dir}/contract1_amendment.jpg",
        width=900,
        height=1400
    )

    # Generate Contract 2 images
    print("\nContract Pair 2: Software License Agreement")
    create_contract_image(
        CONTRACT2_ORIGINAL,
        f"{output_dir}/contract2_original.jpg",
        width=900,
        height=1200
    )
    create_contract_image(
        CONTRACT2_AMENDMENT,
        f"{output_dir}/contract2_amendment.jpg",
        width=900,
        height=1300
    )

    print("\n" + "="*60)
    print("✓ ALL TEST IMAGES GENERATED SUCCESSFULLY")
    print("="*60)
    print(f"\nImages saved to: {output_dir}/")
    print("\nYou can now run the contract comparison system:")
    print("\npython src/main.py \\")
    print(f"  --original {output_dir}/contract1_original.jpg \\")
    print(f"  --amendment {output_dir}/contract1_amendment.jpg")
    print()


if __name__ == "__main__":
    main()
