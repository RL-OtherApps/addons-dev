# Copyright 2018 Kolushov Alexandr <https://it-projects.info/team/KolushovAlexandr>
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl.html).
{
    "name": """POS E-Sign Request""",
    "summary": """Asks Customer For E-Sign On Payment""",
    "category": "Point of Sale",
    # "live_test_url": "http://apps.it-projects.info/shop/product/DEMO-URL?version=10.0",
    "images": [],
    "version": "10.0.1.0.0",
    "application": False,

    "author": "IT-Projects LLC, Kolushov Alexandr",
    "support": "apps@it-projects.info",
    "website": "https://it-projects.info/team/KolushovAlexandr",
    "license": "LGPL-3",
    # "price": 9.00,
    # "currency": "EUR",

    "depends": [
        "pos_longpolling",
    ],
    "external_dependencies": {"python": [], "bin": []},
    "data": [
        "views/assets.xml",
        "views/pos_config_view.xml",
        "views/partner_views.xml",
    ],
    "demo": [
    ],
    "qweb": [
        "static/src/xml/pos_esign.xml",
        "static/src/xml/est_templates.xml",
    ],

    "post_load": None,
    "pre_init_hook": None,
    "post_init_hook": None,
    "uninstall_hook": None,

    "auto_install": False,
    "installable": True,

    # "demo_title": "POS E-Sign Request",
    # "demo_addons": [
    # ],
    # "demo_addons_hidden": [
    # ],
    # "demo_url": "DEMO-URL",
    # "demo_summary": "Asks Customer For E-Sign On Payment",
    # "demo_images": [
    #    "images/MAIN_IMAGE",
    # ]
}
