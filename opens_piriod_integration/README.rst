==============================
Integración de Odoo con Piriod
==============================
Agrega integración entre Odoo y Pairod:

* Fractura (Piriod -> Odoo): Un Webhook de Piriod notifica al endpoint (implementado en este modulo) cuando se crea una
  "factura de cliente" enviando un evento (propio de Piriod) y el id de la factura Piriod. Con este id mediante el API
  de Piriod se obtien los datos de factura y se guardan en odoo. Los datos de factura se guardaran en el modelo
  'account_move', los productos o lineas de produtos se guardan en el modelo 'account_move_line' **No se guarda el
  descuento de la liena de factura ya que Piriod toma el descuento en "porcentaje o monto" y Odoo solo admite
  descuento en porcentaje, aun asi es posible ingresar el desc. de forma manual siempre en formato %**, los datos del
  tipo de documento(ej: "factura_electronica") se buscan y de no existir se crean en el modelo
  'l10n_latam.document.type', los datos del producto se buscan y de no existir un producto con el mismo nombre
  se crea en el modelo 'product.template', por ultimo se buscan los datos del cliente y de no existir cliente con el
  mismo nombre se crea en el modelo 'res.partner'.

Configuración
=============
Para que el Webhook y API de Piriod funcione correctamente.

#. En la configuración general de Odoo -> Compañías -> Actualizar información
    * URL API Piriod: La url oficial de la API de Piriod
    * ID Organización Piriod: ID de organización provisto por Piriod
    * Token Piriod: Token de la cuenta de piriod provisto por Piriod

#. En Piriod configuración de la organización -> webhooks -> Nuevo webhook
    * URL de conexión: **http://url_servidor_de_odoo**/api/piriod_webhook_invoice
    * Eventos: Seleccionar invoice.finalized

        crear el webhook

#. En la configuración general de Odoo -> Cuenta Piriod
    * Cuenta de Piriod: Seleccionar la cuenta de piriod.

Creditos
========

* Opens Solutions

Dependencias
============

#. account
#. l10n_cl
#. l10n_latam_invoice_document