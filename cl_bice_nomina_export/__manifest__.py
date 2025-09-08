{
    "name": "CL: Exportador Nómina Banco BICE (Proveedores)",
    "version": "17.0.2.1.0",
    "summary": "Genera archivo CSV (layout BICE Proveedores) desde Pagos en Lote (Tipo cuenta fijo Corriente).",
    "author": "Branco Barraza",
    "website": "",
    "license": "LGPL-3",
    "depends": ["account"],
    "data": [
        "security/ir.model.access.csv",
        "views/res_bank_views.xml",
        "views/account_batch_payment_views.xml",
        "wizard/bice_export_wizard_views.xml"
    ],
    "application": false
}
