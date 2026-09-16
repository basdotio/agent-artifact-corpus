# WooCommerce CLI Commands Reference

All WooCommerce CLI commands require `--user=<id>` parameter to authenticate.

## Product Management

### List Products
```bash
wp wc product list --user=1
wp wc product list --user=1 --format=json
wp wc product list --user=1 --per_page=50
wp wc product list --user=1 --status=publish
wp wc product list --user=1 --type=simple
wp wc product list --user=1 --featured=true
```

### Create Product
```bash
wp wc product create --user=1 --name="T-Shirt" --type=simple --regular_price=19.99 --sku=TSHIRT001

wp wc product create --user=1 \
  --name="Premium Hoodie" \
  --type=simple \
  --regular_price=49.99 \
  --sale_price=39.99 \
  --sku=HOODIE001 \
  --description="Comfortable premium hoodie" \
  --short_description="Premium quality" \
  --manage_stock=true \
  --stock_quantity=100
```

### Update Product
```bash
wp wc product update 123 --user=1 --regular_price=24.99
wp wc product update 123 --user=1 --stock_quantity=50
wp wc product update 123 --user=1 --sale_price=19.99
```

### Delete Product
```bash
wp wc product delete 123 --user=1
wp wc product delete 123 --user=1 --force
```

### Get Product
```bash
wp wc product get 123 --user=1
wp wc product get 123 --user=1 --format=json
```

## Customer Management

### List Customers
```bash
wp wc customer list --user=1
wp wc customer list --user=1 --format=json
wp wc customer list --user=1 --role=customer
```

### Create Customer
```bash
wp wc customer create --user=1 \
  --email=customer@example.com \
  --first_name=John \
  --last_name=Doe \
  --username=johndoe \
  --password=securepass123
```

With billing and shipping:
```bash
wp wc customer create --user=1 \
  --email=customer@example.com \
  --first_name=John \
  --last_name=Doe \
  --username=johndoe \
  --password=securepass123 \
  --billing='{"first_name":"John","last_name":"Doe","company":"ACME","address_1":"123 Main St","city":"New York","state":"NY","postcode":"10001","country":"US","email":"john@example.com","phone":"555-1234"}' \
  --shipping='{"first_name":"John","last_name":"Doe","company":"ACME","address_1":"123 Main St","city":"New York","state":"NY","postcode":"10001","country":"US"}'
```

### Update Customer
```bash
wp wc customer update 17 --user=1 --first_name=Jane
wp wc customer update 17 --user=1 --email=newemail@example.com
```

### Delete Customer
```bash
wp wc customer delete 17 --user=1
wp wc customer delete 17 --user=1 --force --reassign=1
```

## Order Management

### List Orders
```bash
wp wc shop_order list --user=1
wp wc shop_order list --user=1 --status=processing
wp wc shop_order list --user=1 --customer=5
wp wc shop_order list --user=1 --format=json
```

### Create Order
```bash
wp wc shop_order create --user=1 \
  --customer_id=5 \
  --line_items='[{"product_id":123,"quantity":2}]' \
  --billing='{"first_name":"John","last_name":"Doe","address_1":"123 Main St","city":"New York","state":"NY","postcode":"10001","country":"US","email":"john@example.com","phone":"555-1234"}'
```

### Update Order
```bash
wp wc shop_order update 355 --user=1 --status=completed
wp wc shop_order update 355 --user=1 --customer_note="Thank you for your order"
```

### Delete Order
```bash
wp wc shop_order delete 355 --user=1
wp wc shop_order delete 355 --user=1 --force
```

## Order Notes

### List Order Notes
```bash
wp wc order_note list 355 --user=1
wp wc order_note list 355 --user=1 --type=customer
```

### Create Order Note
```bash
wp wc order_note create 355 --user=1 --note="Package shipped" --customer_note=true
wp wc order_note create 355 --user=1 --note="Internal note" --customer_note=false
```

### Delete Order Note
```bash
wp wc order_note delete 355 286 --user=1 --force
```

## Coupon Management

### List Coupons
```bash
wp wc shop_coupon list --user=1
wp wc shop_coupon list --user=1 --format=json
```

### Create Coupon
```bash
wp wc shop_coupon create --user=1 \
  --code=SUMMER20 \
  --discount_type=percent \
  --amount=20 \
  --description="Summer sale 20% off"

wp wc shop_coupon create --user=1 \
  --code=FREESHIP \
  --discount_type=fixed_cart \
  --amount=0 \
  --free_shipping=true \
  --minimum_amount=50
```

### Update Coupon
```bash
wp wc shop_coupon update 45 --user=1 --amount=25
wp wc shop_coupon update 45 --user=1 --discount_type=percent --free_shipping=true
```

### Delete Coupon
```bash
wp wc shop_coupon delete 45 --user=1
wp wc shop_coupon delete 45 --user=1 --force
```

## Product Categories

### List Categories
```bash
wp wc product_cat list --user=1
wp wc product_cat list --user=1 --format=json
```

### Create Category
```bash
wp wc product_cat create --user=1 --name="Electronics"
wp wc product_cat create --user=1 --name="Laptops" --parent=5 --description="Computer laptops"
```

### Update Category
```bash
wp wc product_cat update 10 --user=1 --name="New Electronics"
```

### Delete Category
```bash
wp wc product_cat delete 10 --user=1 --force
```

## Product Tags

### List Tags
```bash
wp wc product_tag list --user=1
```

### Create Tag
```bash
wp wc product_tag create --user=1 --name="Featured"
```

### Update Tag
```bash
wp wc product_tag update 15 --user=1 --name="Best Seller"
```

### Delete Tag
```bash
wp wc product_tag delete 15 --user=1 --force
```

## Product Variations

### List Variations
```bash
wp wc product_variation list 200 --user=1
```

### Create Variation
```bash
wp wc product_variation create 200 --user=1 \
  --regular_price=29.99 \
  --sku=SHIRT-RED-M \
  --attributes='[{"id":1,"option":"Red"},{"id":2,"option":"Medium"}]'
```

### Update Variation
```bash
wp wc product_variation update 200 301 --user=1 --stock_quantity=50
```

### Delete Variation
```bash
wp wc product_variation delete 200 301 --user=1 --force
```

## Product Attributes

### List Attributes
```bash
wp wc product_attribute list --user=1
```

### Create Attribute
```bash
wp wc product_attribute create --user=1 --name="Size" --type=select
```

### Update Attribute
```bash
wp wc product_attribute update 5 --user=1 --name="Sizes"
```

## Payment Gateways

### List Gateways
```bash
wp wc payment_gateway list --user=1
```

### Get Gateway
```bash
wp wc payment_gateway get bacs --user=1
```

### Update Gateway
```bash
wp wc payment_gateway update bacs --user=1 --enabled=true
```

## Shipping

### List Shipping Zones
```bash
wp wc shipping_zone list --user=1
```

### Create Shipping Zone
```bash
wp wc shipping_zone create --user=1 --name="Domestic"
```

### List Shipping Methods
```bash
wp wc shipping_zone_method list 1 --user=1
```

### Create Shipping Method
```bash
wp wc shipping_zone_method create 1 --user=1 --method_id=flat_rate
```

## Tax

### List Tax Rates
```bash
wp wc tax list --user=1
```

### Create Tax Rate
```bash
wp wc tax create --user=1 \
  --country=US \
  --state=CA \
  --rate=7.5 \
  --name="California Sales Tax" \
  --shipping=true
```

### Update Tax Rate
```bash
wp wc tax update 5 --user=1 --rate=8.0
```

## Webhooks

### List Webhooks
```bash
wp wc webhook list --user=1
```

### Create Webhook
```bash
wp wc webhook create --user=1 \
  --name="Order Created" \
  --topic=order.created \
  --delivery_url=https://example.com/webhook \
  --secret=mysecretkey
```

### Update Webhook
```bash
wp wc webhook update 10 --user=1 --status=active
```

## System Tools

### List Tools
```bash
wp wc tool list --user=1
```

### Run Tool
```bash
wp wc tool run clear_transients --user=1
```

## Settings

### Get Setting
```bash
wp wc setting get general --user=1
```

### Update Setting
```bash
wp wc setting update general woocommerce_default_country --value=US --user=1
```

## Common WooCommerce Workflows

### Setup New Store
```bash
# Create products
wp wc product create --user=1 --name="Product 1" --type=simple --regular_price=29.99
wp wc product create --user=1 --name="Product 2" --type=simple --regular_price=39.99

# Create categories
wp wc product_cat create --user=1 --name="Electronics"

# Create coupon
wp wc shop_coupon create --user=1 --code=WELCOME10 --discount_type=percent --amount=10

# Enable payment gateway
wp wc payment_gateway update bacs --user=1 --enabled=true
```

### Bulk Product Import
```bash
# Create multiple products from a loop
for i in {1..10}; do
  wp wc product create --user=1 \
    --name="Product $i" \
    --type=simple \
    --regular_price=$((20 + i)) \
    --sku="PROD00$i"
done
```

### Order Processing
```bash
# Get all processing orders
wp wc shop_order list --user=1 --status=processing --format=ids

# Update order status
wp wc shop_order update 355 --user=1 --status=completed

# Add order note
wp wc order_note create 355 --user=1 --note="Shipped via FedEx" --customer_note=true
```

### Customer Management
```bash
# List customers with orders
wp wc customer list --user=1 --format=json | jq '.[] | select(.orders_count > 0)'

# Get customer in CSV format
wp wc customer get 17 --user=1 --format=csv
```

## Output Formats

All WooCommerce commands support multiple formats:

```bash
--format=table   # Default table view
--format=json    # JSON output
--format=csv     # CSV output
--format=ids     # Space-separated IDs
--format=yaml    # YAML output
```

## Useful Flags

- `--porcelain` - Output only the ID for create/update operations
- `--force` - Force deletion (bypass trash)
- `--fields=<fields>` - Limit output to specific fields
- `--field=<field>` - Get value of single field

## Examples from Real Usage

### Create Customer with Full Details
```bash
wp wc customer create --user=1 \
  --email=woo@woo.local \
  --billing='{"first_name":"Bob","last_name":"Tester","company":"Woo","address_1":"123 Main St.","city":"New York","state":"NY","country":"USA"}' \
  --shipping='{"first_name":"Bob","last_name":"Tester","company":"Woo","address_1":"123 Main St.","city":"New York","state":"NY","country":"USA"}' \
  --password=hunter2 \
  --username=mrbob \
  --first_name=Bob \
  --last_name=Tester
```

### Clear Product Cache
```bash
wp wc tool run clear_transients --user=1
```

### Get Customer Download Links
```bash
wp wc customer_download list 17 --user=1
```

## Common Issues

### User Authentication
Always include `--user=1` or another admin user ID. Without this, commands will fail with permission errors.

### JSON Formatting
When using complex objects (billing, shipping, line_items), ensure proper JSON escaping:
```bash
--billing='{"first_name":"John","last_name":"Doe"}'
```

### Product Creation
Minimum required: `--name`, `--type`, and `--regular_price`

## Integration with Blueprints

Use WP-CLI in blueprints via the `wp-cli` step:

```json
{
  "extraLibraries": ["wp-cli"],
  "steps": [
    {
      "step": "wp-cli",
      "command": "wc product create --user=1 --name='Demo Product' --type=simple --regular_price=29.99"
    }
  ]
}
```
