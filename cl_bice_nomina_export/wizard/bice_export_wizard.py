# -*- coding: utf-8 -*-
import base64
import csv
from io import StringIO

from odoo import api, fields, models


class BiceExportWizard(models.TransientModel):
    _name = "bice.export.wizard"
    _description = "Exportar archivo Proveedores Banco BICE"

    batch_id = fields.Many2one(
        "account.batch.payment",
        string="Batch",
        required=True,
        default=lambda self: self.env.context.get("default_batch_id"),
    )
    archivo = fields.Binary(string="Archivo", readonly=True)
    nombre = fields.Char(string="Nombre", default="proveedores.csv", required=True)

    def _build_csv_content(self):
        """Genera contenido CSV simple de ejemplo con pagos del lote.
        Ajusta aquí las columnas reales del layout BICE si las necesitas.
        """
        self.ensure_one()
        output = StringIO()
        writer = csv.writer(output, delimiter=";", lineterminator="\n")

        # Cabecera (opcional, puedes quitarla si BICE no la quiere)
        writer.writerow(["Partner", "RUT/ID", "Cuenta", "Banco", "Monto", "Moneda"])

        for payment in self.batch_id.payment_ids:
            partner = payment.partner_id
            bank_account = partner.bank_ids[:1]  # primera cta bancaria
            account_number = bank_account.acc_number or ""
            bank_name = bank_account.bank_id.name or ""
            amount = f"{payment.amount:.2f}"
            currency = payment.currency_id.name or "CLP"
            rut = partner.vat or ""  # si usas RUT en vat

            writer.writerow([
                partner.name or "",
                rut,
                account_number,
                bank_name,
                amount,
                currency,
            ])

        return output.getvalue()

    def action_generate(self):
        self.ensure_one()

        # 1) Armar CSV
        csv_text = self._build_csv_content()
        csv_bytes = csv_text.encode("utf-8")
        b64 = base64.b64encode(csv_bytes)

        # 2) Guardar en el wizard (por si quieres verlo)
        self.write({"archivo": b64})

        # 3) Crear adjunto en el Lote
        attachment = self.env["ir.attachment"].create({
            "name": self.nombre or "proveedores.csv",
            "datas": b64,
            "res_model": "account.batch.payment",
            "res_id": self.batch_id.id,
            "mimetype": "text/csv",
            "type": "binary",
        })

        # 4) Postear mensaje en el lote
        self.batch_id.message_post(
            body=f"Archivo BICE generado: <b>{attachment.name}</b> (adjunto)",
            attachment_ids=[attachment.id],
        )

        # 5) Disparar descarga directa del adjunto
        return {
            "type": "ir.actions.act_url",
            "url": f"/web/content/{attachment.id}?download=true",
            "target": "self",
        }

