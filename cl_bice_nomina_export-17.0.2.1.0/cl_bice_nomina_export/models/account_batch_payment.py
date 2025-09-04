from odoo import models

class AccountBatchPayment(models.Model):
    _inherit = "account.batch.payment"

    def action_export_bice_nomina(self):
        self.ensure_one()
        return {
            "name": "Exportar BICE Proveedores",
            "type": "ir.actions.act_window",
            "res_model": "bice.export.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {
                "default_batch_id": self.id,
                "default_journal_id": self.journal_id.id,
            },
        }
