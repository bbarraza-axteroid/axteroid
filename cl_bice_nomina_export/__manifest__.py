{
    "name": "CL: Exportador Nómina Banco BICE (Proveedores)",
    "version": "17.0.2.1.1",
    "summary": "Genera archivo CSV (layout BICE Proveedores) desde Pagos en Lote.",
    "author": "Branco_Barraza",
    "website": "",
    "license": "LGPL-3",
    "depends": ["account", "account_batch_payment"],
    "data": [
        "security/ir.model.access.csv",
        "views/res_bank_views.xml",

        # Primero: wizard (crea la ACCIÓN que luego usa el botón)
        "wizard/bice_export_wizard_views.xml",

        # Después: la vista que añade el botón al lote de pagos
        "views/account_batch_payment_views.xml",
    ],
    "application": False,
}
