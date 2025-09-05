{
    "name": "CL: Exportador Nómina Banco BICE (Proveedores)",
    "version": "17.0.2.1.1",
    "summary": "Genera archivo CSV (layout BICE Proveedores) desde Pagos en Lote (Tipo cuenta fijo Corriente).",
    "author": "ChatGPT",
    "website": "",
    "license": "LGPL-3",
    "depends": ["account", "account_batch_payment"],
    "data": [
        "security/ir.model.access.csv",
        "views/res_bank_views.xml",                # si no lo usas, puedes quitar esta línea
        "views/account_batch_payment_views.xml",
        "wizard/bice_export_wizard_views.xml"      # <- tu manifest ya lo apunta así
    ],
    "application": False,
    "installable": True,
}
