# -*- coding: utf-8 -*-

import logging
from odoo import models, fields, api, _
_logger = logging.getLogger(__name__)


class ResConfigSetting(models.TransientModel):

    _inherit = "res.config.settings"

    return_picking_type_id = fields.Many2one(comodel_name="stock.picking.type",
                                             string="Internal Transfer With Cost Return Type",
                                             related="company_id.return_picking_type_id",
                                             readonly=False)
    internal_receipt_id = fields.Many2one(comodel_name="stock.picking.type",
                                          string="Internal Transfer With Cost Receipt Type",
                                          related="company_id.internal_receipt_id",
                                          readonly=False)



