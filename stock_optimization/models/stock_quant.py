# -*- coding: utf-8 -*-

import logging
from odoo import models, fields
from odoo.addons.queue_job.job import job

_logger = logging.getLogger(__name__)

class StockPicking(models.Model):
    _inherit = "stock.picking"

    @job
    def button_validate_job(self,ids):
        self.env['stock.picking'].browse(ids).button_validate()


    def do_button_validate_job(self):
        self.env['stock.picking'].with_delay(priority=1,description=self.name).button_validate_job(self.id)

class StockQuant(models.Model):

    _inherit = "stock.quant"

    product_id = fields.Many2one('product.product', 'Product',ondelete='restrict',index=True, readonly=True, required=True)
    product_tmpl_id = fields.Many2one('product.template', string='Product Template',index=True,related='product_id.product_tmpl_id', readonly=False)
    location_id = fields.Many2one('stock.location', 'Location',index=True,auto_join=True, ondelete='restrict', readonly=True, required=True)
    lot_id = fields.Many2one('stock.production.lot', 'Lot/Serial Number',ondelete='restrict',index=True, readonly=True)
    product_uom_id = fields.Many2one('uom.uom', 'Unit of Measure',readonly=True,index=True,related='product_id.uom_id')
