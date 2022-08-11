from odoo import fields, models, api
from ast import literal_eval


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    piriod_account_id = fields.Many2one('account.account', string="Cuenta de Piriod")

    @api.model
    def get_values(self):
        res = super(ResConfigSettings, self).get_values()
        ir_config = self.env['ir.config_parameter'].sudo()

        piriod_account_id = ir_config.get_param('piriod_account_id')

        res.update(
            piriod_account_id = literal_eval(piriod_account_id) if piriod_account_id else None
        )
        return res

    def set_values(self):
        super(ResConfigSettings, self).set_values()
        ir_config = self.env['ir.config_parameter'].sudo()

        ir_config.set_param('piriod_account_id', self.piriod_account_id.id)