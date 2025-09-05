# cl_bice_nomina_export/__manifest__.py
{
    "name": "CL: Exportador Nómina Banco BICE (Proveedores)",
    "version": "17.0.1.0.0",
    "author": "Beagle",
    "category": "Accounting",
    "depends": ["account", "account_batch_payment"],
    "data": [
        # PRIMERO: acción + vista del wizard
        "wizard/bice_export_wizard_views.xml",
        # DESPUÉS: herencia de la vista de lotes con el botón
        "views/account_batch_payment_views.xml",
        # (si tienes security/ir.model.access.csv déjalo aquí también)
    ],
    "installable": True,
}
