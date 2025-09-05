import base64
import os
from odoo import models, fields, api
from odoo.exceptions import UserError
from datetime import datetime


class AccountBatchPayment(models.Model):
    _inherit = 'account.batch.payment'

    def export_bice_proveedores_file(self):
        self.ensure_one()

        export_lines = []

        for payment in self.payment_ids:
            partner = payment.partner_id

            if not partner.l10n_cl_rut:
                raise UserError(f"El proveedor {partner.name} no tiene RUT configurado.")

            rut = partner.l10n_cl_rut.replace('.', '').replace('-', '')
            rut = rut.zfill(10)

            # Nombre: 40 caracteres, izquierda, relleno con espacios
            name = partner.name[:40].ljust(40)

            # Monto: 13 posiciones, sin punto decimal, relleno con ceros a la izquierda
            amount = str(int(payment.amount)).zfill(13)

            # Número cuenta: 20 caracteres, derecha, relleno con espacios
            account_number = (partner.bank_account_id.acc_number or '').rjust(20)

            # Banco: 3 dígitos (debe tener configurado el código)
            bank_code = partner.bank_id.bic or '000'
            bank_code = bank_code.zfill(3)

            # Tipo cuenta: 2 dígitos (corriente = 1, vista = 2, ahorro = 3)
            account_type = partner.bank_account_id.account_type or '1'
            account_type = account_type.zfill(2)

            # Email: 50 caracteres
            email = (partner.email or '').ljust(50)

            # Referencia: 40 caracteres
            ref = (payment.ref or '').ljust(40)

            # Fecha de proceso: formato DDMMYYYY
            process_date = datetime.now().strftime('%d%m%Y')

            # Línea final con todos los campos concatenados
            line = (
                rut +
                name +
                amount +
                account_number +
                bank_code +
                account_type +
                email +
                ref +
                process_date
            )

            export_lines.append(line)

        output = "\r\n".join(export_lines) + "\r\n"

        filename = f"nomina_bice_proveedores_{datetime.now().strftime('%Y%m%d')}.csv"

        export_file = base64.b64encode(output.encode('utf-8'))

        wizard = self.env['bice.export.wizard'].create({
            'file_data': export_file,
            'file_name': filename,
        })

        return {
            'type': 'ir.actions.act_url',
            'url': f"/web/content/?model=bice.export.wizard&id={wizard.id}&field=file_data&filename_field=file_name&download=true",
            'target': 'new',
        }
