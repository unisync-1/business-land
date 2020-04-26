# -*- coding: utf-8 -*-

import logging
from odoo import models, fields
_logger = logging.getLogger(__name__)


class StockQuant(models.Model):

    _inherit = "stock.quant"

    product_id = fields.Many2one('product.product', 'Product',ondelete='restrict',index=True, readonly=True, required=True)
    product_tmpl_id = fields.Many2one('product.template', string='Product Template',index=True,related='product_id.product_tmpl_id', readonly=False)
    location_id = fields.Many2one('stock.location', 'Location',index=True,auto_join=True, ondelete='restrict', readonly=True, required=True)
    lot_id = fields.Many2one('stock.production.lot', 'Lot/Serial Number',ondelete='restrict',index=True, readonly=True)
    product_uom_id = fields.Many2one('uom.uom', 'Unit of Measure',readonly=True,index=True,related='product_id.uom_id')
