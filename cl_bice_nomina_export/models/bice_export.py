# cl_bice_nomina_export/models/bice_export.py
from odoo import models

class AccountBatchPayment(models.Model):
    _inherit = 'account.batch.payment'

    def action_export_bice(self):
        return {
            'name': 'Exportar BICE',
            'type': 'ir.actions.act_window',
            'res_model': 'bice.export.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_batch_payment_id': self.id},
        }
