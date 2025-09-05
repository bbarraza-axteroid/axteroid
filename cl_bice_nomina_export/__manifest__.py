{
    "name": "CL: Exportador Nómina Banco BICE (Proveedores)",
    "version": "17.0.2.1.1",
    "summary": "Genera archivo CSV (layout BICE Proveedores) desde Pagos en Lote.",
    "category": "Accounting/Payments",
    "author": "Axteroid",
    "license": "LGPL-3",
    "depends": ["account", "account_batch_payment"],   # <- AÑADIDO
    "data": [
        "security/ir.model.access.csv",
        "views/res_bank_views.xml",
        "views/account_batch_payment_views.xml",
        "wizard/bice_export_wizard_views.xml",
    ],
    "installable": True,
    "application": False,
}
