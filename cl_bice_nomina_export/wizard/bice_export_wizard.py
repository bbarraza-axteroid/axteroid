# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError
import unicodedata
import re
from io import StringIO, BytesIO

# --- Mapea tipo de cuenta de Odoo -> código banco (1 vista, 2 ahorro, 3 corriente)
ACCOUNT_TYPE_MAP = {
    # ajusta a tus valores reales
    'saving': '2',
    'savings': '2',
    'ahorro': '2',
    'current': '3',
    'corriente': '3',
    'checking': '3',
    'vista': '1',
    'rut': '1',
    'cuenta_vista': '1',
}

# --- Mapea bancos a códigos CCA (agrega/ajusta los que uses)
BANK_CODE_MAP = {
    # ejemplos, completa según la tabla CCA que usan con BICE
    # 'BANCO ESTADO': '12',
    # 'BANCO DE CHILE': '01',
    # 'BANCO BICE': '28',
    # usa un identificador estable: bank_id.code, bank_id.bic o bank_id.name normalizado
}

def _strip_accents(value):
    if not value:
        return ''
    txt = unicodedata.normalize('NFKD', value)
    txt = ''.join([c for c in txt if not unicodedata.combining(c)])
    # quita explícitamente ñ/Ñ
    txt = txt.replace('ñ', 'n').replace('Ñ', 'N')
    return txt

def _only_alnum_and_basic(value, maxlen=None):
    """ Letras y números; también permite .-_ para mail si lo necesitas en otra función """
    if not value:
        return ''
    v = _strip_accents(value)
    v = re.sub(r'[^A-Za-z0-9 ]', '', v)  # sólo alfanum y espacios
    v = re.sub(r'\s+', ' ', v).strip()
    if maxlen:
        v = v[:maxlen]
    return v

def _sanitize_name(name):
    # Hasta 40 caracteres, sin puntos, guion, ni tildes
    v = _only_alnum_and_basic(name, 40)
    return v

def _sanitize_rut(vat):
    """RUT sin puntos ni guion, hasta 11 caract. Elimina todo menos dígitos y K/k."""
    if not vat:
        return ''
    s = vat.upper()
    s = re.sub(r'[^0-9K]', '', s)  # deja dígitos y K
    return s[:11]

def _sanitize_account(number):
    """Hasta 17 caracteres, deja sólo dígitos y letras (por si algunos bancos entregan letras)"""
    if not number:
        return ''
    s = re.sub(r'[^0-9A-Za-z]', '', number)
    return s[:17]

def _sanitize_factura(text):
    # Obligatorio, hasta 15, sin espacios
    if not text:
        return ''
    t = _strip_accents(text)
    t = re.sub(r'\s+', '', t)
    t = re.sub(r'[^A-Za-z0-9]', '', t)
    return t[:15]

def _mail_ok(mail):
    """Máx 50; letras y números, permite . - _ y @; sin Ñ/ñ"""
    if not mail:
        return ''
    m = _strip_accents(mail)
    m = re.sub(r'[^A-Za-z0-9\.\-\_@]', '', m)
    return m[:50]

def _bank_code_from_record(bank_rec):
    """
    Intenta obtener el código CCA del banco.
    - Si tienes un campo 'code' en res.bank con el código CCA úsalo.
    - Si no, normaliza el nombre y busca en el dict BANK_CODE_MAP.
    """
    if not bank_rec:
        return ''
    # 1) si ya guardas el código CCA en bank_rec.code (o un campo propio)
    if getattr(bank_rec, 'code', False):
        return str(bank_rec.code)
    # 2) por nombre normalizado
    key = _only_alnum_and_basic(bank_rec.name or '').upper()
    return BANK_CODE_MAP.get(key, '')

class BiceExportWizard(models.TransientModel):
    _name = 'bice.export.wizard'
    _description = 'Exportar archivo Proveedores Banco BICE'

    batch_id = fields.Many2one('account.batch.payment', required=True)
    nombre = fields.Char(default='proveedores.csv')
    archivo = fields.Binary(readonly=True)

    def _gather_payments(self):
        """
        Toma los pagos del lote. Ajusta si usas otro domain o si el botón
        puede abrir el wizard desde otra pantalla.
        """
        self.ensure_one()
        payments = self.batch_id.payment_ids.filtered(lambda p: p.state in ('posted', 'sent'))
        if not payments:
            raise UserError(_('No hay pagos en el lote para exportar.'))
        return payments

    def _row_for_payment(self, pay):
        """
        Devuelve una lista de columnas según layout Proveedores BICE:
        [Nombre, Rut, Cuenta, Monto, Banco, TipoCuenta, Moneda, OfOr, OfDe, Factura, Mail]
        - Sin encabezados
        """
        partner = pay.partner_id
        partner_bank = pay.partner_bank_id  # cuenta de pago
        bank_rec = partner_bank.bank_id if partner_bank else False

        # 1) Nombre Titular (<=40, sin puntos/guion/tildes)
        nombre = _sanitize_name(partner.name or '')

        # 2) RUT (<=11, sin puntos ni guion)
        rut = _sanitize_rut(partner.vat or '')

        # 3) Cuenta (<=17)
        cuenta = _sanitize_account(partner_bank.acc_number if partner_bank else '')

        # 4) Monto (hasta 11 cifras enteras, CLP → entero)
        # si tu monto está en CLP con decimales 0, simplemente redondea
        amount = int(round(abs(pay.amount)))
        monto = str(amount)[:11]

        # 5) Banco (código CCA)
        banco_code = _bank_code_from_record(bank_rec)
        if not banco_code:
            # Si no encuentras código, lanza error para evitar archivos inválidos
            raise UserError(_("No se encontró código de banco CCA para '%s'") % (bank_rec.name if bank_rec else ''))

        # 6) Tipo de cuenta (1 vista, 2 ahorro, 3 corriente)
        acc_type_raw = (partner_bank.acc_type or '').lower() if partner_bank else ''
        tipo_cuenta = ACCOUNT_TYPE_MAP.get(acc_type_raw, '')
        if not tipo_cuenta:
            # intenta por nombre en etiqueta
            label = (partner_bank.bank_id and partner_bank.bank_id.name or '').lower()
            tipo_cuenta = ACCOUNT_TYPE_MAP.get(label, '')
        if not tipo_cuenta:
            raise UserError(_("No se pudo determinar el tipo de cuenta (1/2/3) para la cuenta %s") % (partner_bank.acc_number if partner_bank else ''))

        # 7) Moneda (siempre "0" para CLP)
        moneda = '0'

        # 8) Oficina Origen y 9) Oficina Destino (siempre "1")
        of_origen = '1'
        of_destino = '1'

        # 10) Factura (obligatorio) — yo usaré ref del pago; ajusta a tu lógica
        factura_src = pay.ref or pay.name or self.batch_id.name or 'FAC12345'
        factura = _sanitize_factura(factura_src)
        if not factura:
            raise UserError(_("No hay referencia para 'Factura' en el pago %s") % (pay.name))

        # 11) Mail beneficiario (opcional)
        email = _mail_ok(partner.email or '')

        return [nombre, rut, cuenta, monto, banco_code, tipo_cuenta, moneda, of_origen, of_destino, factura, email]

    def _generate_csv_bytes(self, payments):
        # Sin encabezados. Separador coma. Fin de línea CRLF recomendado para bancos.
        buf = StringIO(newline='')
        for p in payments:
            cols = self._row_for_payment(p)
            # Escapar comas si llegasen a quedar; aquí sanitizamos para que no haya comillas.
            line = ",".join(cols)
            buf.write(line + "\r\n")
        data = buf.getvalue().encode('utf-8')
        return data

    def action_generate(self):
        self.ensure_one()
        pays = self._gather_payments()
        csv_bytes = self._generate_csv_bytes(pays)

        # 1) Poner en el wizard para descargar
        self.write({
            'archivo': csv_bytes.encode('base64') if isinstance(csv_bytes, str) else csv_bytes,
        })

        # 2) Adjuntar al lote y postear en el chatter
        att = self.env['ir.attachment'].create({
            'name': self.nombre or 'proveedores.csv',
            'datas': csv_bytes.encode('base64') if isinstance(csv_bytes, str) else csv_bytes,
            'res_model': 'account.batch.payment',
            'res_id': self.batch_id.id,
            'mimetype': 'text/csv',
        })
        self.batch_id.message_post(body=_("Archivo BICE generado: <b>%s</b> (adjunto)") % (att.name,), attachment_ids=[att.id])

        # Devolver vista del wizard para que el usuario pueda “Guardar”/descargar
        return {
            'type': 'ir.actions.act_window',
            'name': _("Exportar BICE Proveedores"),
            'res_model': 'bice.export.wizard',
            'view_mode': 'form',
            'res_id': self.id,
            'target': 'new',
        }
