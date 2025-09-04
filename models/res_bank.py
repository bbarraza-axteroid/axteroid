from odoo import fields, models

class ResBank(models.Model):
    _inherit = "res.bank"

    l10n_cl_sbif_code = fields.Char(
        string="Código banco (CCA/CMF)",
        help="Código numérico del banco según CCA/CMF requerido por el layout bancario (p.ej., 028=BICE, 037=Santander)."
    )
