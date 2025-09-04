from odoo import fields, models

class ResPartnerBank(models.Model):
    _inherit = "res.partner.bank"

    l10n_cl_account_type = fields.Selection(
        [
            ("CT", "Cuenta Corriente"),
            ("AH", "Cuenta de Ahorro"),
            ("VP", "Cuenta Vista/RUT"),
            ("OT", "Otra"),
        ],
        string="Tipo de cuenta (CL)",
        help="Tipo de cuenta requerido por los formatos bancarios chilenos.",
    )
