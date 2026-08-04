=== Amazon Source Bridge ===
Contributors: you
Tags: woocommerce, catalog, dropship, on-demand-products
Requires at least: 6.0
Requires PHP: 7.4
Tested up to: 6.6
Stable tag: 0.1.0

Show materialized products from an external catalog service when a shopper
searches for something you don't stock. Real WooCommerce products get
created only when an order is placed.

== How it works ==

1.  Shopper searches on your WooCommerce site.
2.  If the term matches the external catalog, the plugin renders those
    hits under the native product loop using WooCommerce's own CSS classes
    so your theme styles them the same as real products.
3.  Shopper clicks a match → phantom product page. First visit kicks off
    background materialization on the FastAPI service; page auto-refreshes
    every 6 seconds until the AI image and rewritten copy are ready
    (typically 30–60 seconds).
4.  "Add to cart" triggers force-materialization if needed, then creates a
    WooCommerce product with `draft` status (invisible to public listings).
    The draft is added to the cart and the shopper is redirected to
    checkout.
5.  When the order is placed (`woocommerce_new_order`), the draft flips to
    `publish` — the product is now a real WooCommerce product tied to the
    order.
6.  A daily cron cleans up phantom drafts that never got ordered (older
    than 24 hours).

== Setup ==

1.  Install the plugin (upload the `amazon-source-bridge/` folder to
    `wp-content/plugins/` and activate).
2.  Go to Settings → Amazon Source Bridge.
3.  Set API URL (your FastAPI service, e.g.
    `https://api.yourdomain.com`) and API Key (matching the
    `SERVICE_API_KEY` env var on the service).
4.  Save. Visit `/shop/?s=<term>` and confirm hits appear.

== Design notes ==

* The plugin never stores your API key on the client side.
* Product images are sideloaded into the WordPress Media Library on
  add-to-cart so they survive if the R2 bucket is later reorganized.
* Product `_visibility` is set to `hidden` even after publish, so the
  materialized product doesn't clutter the shop grid — customers only
  reach it via search or their own order history.
