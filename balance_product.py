# -*- coding: utf-8 -*-
#This file is part of Tryton.  The COPYRIGHT file at the top level of
#this repository contains the full copyright notices and license terms.
##############################################################################
# В данном файле описываются объекты 
# 3. Тип счетов
# 3. Остатки по счетам
# 3. 
# 3. 
##############################################################################
#UPDATE account_ru_book_cash_test
#   SET debit=debit+12, credit=credit-10
#    WHERE reference in ('111,22', '333,33');
"Balances Accounting"
from trytond.model import ModelView, ModelSQL, fields
from trytond.transaction import Transaction
from decimal import Decimal
import datetime

#
# Остатки по счетам за периоды (Товарно-материальные ценности)
#
class BalanceProductFixedAssets(ModelSQL, ModelView):
    _name = "ekd.balances.fixed_assets"

    def __init__(self):
        super(BalanceProductFixedAssets, self).__init__()

        self._error_messages.update({
            'unknown_direct_account':'Unknow Direct Account for Balance!',
            'balance_account_done': 'Balance Account:%s is Done!',
            'balance_account_not_find': 'Balance Account not find!',
        })

    def post_balance(self, values=None):
        '''
         Изменение остатка и оборота в учетном регистре счета
            values = {'company': ID учетной организации,
                      'period': Дата операции,
                      'account': ID счета,
                      'party': ID организации,
                      'product': ID ТМЦ или услуги,
                      'product_uom': ID Ед.измерения ТМЦ или услуги,
                      'unit_price': ID Цена за единицу ТМЦ или услуги,
                      'quantity': Кол-во,
                      'amount': сумма, }
                      'currency': Валюта поля сумма, }
        '''
        if values == None:
            return False

        if values.get('account_kind', 'balance') == 'off_balance_out':
            balance_id = self.search([
                        ('account','=', values.get('account')),
                        ('party','=',values.get('party')),
                        ('product','=',values.get('product')),
                        ('product_uom','=',values.get('product_uom')),
                        ('unit_price','=',values.get('unit_price')),
                        ], limit=1)
        else:
            balance_id = self.search([
                        ('period','=',values.get('period')),
                        ('account','=', values.get('account')),
                        ('party','=',values.get('party')),
                        ('product','=',values.get('product')),
                        ('product_uom','=',values.get('product_uom')),
                        ('unit_price','=',values.get('unit_price')),
                        ], limit=1)

        if len(balance_id):
            if isinstance(balance_id, list):
                balance_id = balance_id[0]

            balance = self.browse(balance_id)

            if balance.state =='done':
                self.raise_user_error('balance_account_done')

            self.write(balance_id, {
                        'qdebit': balance.qdebit+values.get('qdebit', 0.0),
                        'debit': balance.debit+values.get('debit',Decimal('0.0')),
                        'qcredit': balance.qcredit+values.get('qcredit', 0.0),
                        'credit': balance.credit+values.get('credit',Decimal('0.0')),
                        })
            if balance.transfer and values.get('transfer',True):
                self.transfer_balance(balance.transfer.id, {
                            'qbalance':balance.qbalance_end,
                            'balance':balance.balance_end,
                            'transfer': values.get('transfer',True)
                            })
        else:
            if values.get('account_kind', 'balance') == 'off_balance_out':
                balance_id = self.create({
                        'company': values.get('company'),
                        'account': values.get('account'),
                        'party': values.get('party'),
                        'product': values.get('product'),
                        'product_uom': values.get('product_uom'),
                        'unit_price': values.get('unit_price'),
                        'qbalance': qbalance_prev,
                        'balance': balance_prev,
                        'qdebit': values.get('qdebit', 0.0),
                        'debit': values.get('debit', Decimal('0.0')),
                        'qcredit': values.get('qcredit', 0.0),
                        'credit': values.get('credit', Decimal('0.0')),
                        })
            else:
                period_obj = self.pool.get('ekd.period')
                period_prev = period_obj.search([
                        ('company','=',values.get('company')),
                        ('end_date','<',values.get('date_operation')),
                        ], order=[('end_date','DESC')], limit=1)
                if isinstance(period_prev, list) and period_prev:
                    period_prev = period_prev[0]

                qbalance_prev= Decimal('0.0')
                balance_prev= Decimal('0.0')
                balance_prev_id = self.search([
                        ('period','=', period_prev),
                        ('account','=', values.get('account')),
                        ('party','=',values.get('party')),
                        ('product','=',values.get('product')),
                        ('product_uom','=',values.get('product_uom')),
                        ('unit_price','=',values.get('unit_price')),
                        ], limit=1)
                for bal_prev in self.browse(balance_prev_id):
                    qbalance_prev = bal_prev.qbalance_end
                    balance_prev = bal_prev.balance_end

                balance_id = self.create({
                        'company': values.get('company'),
                        'period': values.get('period'),
                        'account': values.get('account'),
                        'party': values.get('party'),
                        'product': values.get('product'),
                        'product_uom': values.get('product_uom'),
                        'unit_price': values.get('unit_price'),
                        'qbalance': qbalance_prev,
                        'balance': balance_prev,
                        'qdebit': values.get('qdebit', 0.0),
                        'debit': values.get('debit', Decimal('0.0')),
                        'qcredit': values.get('qcredit', 0.0),
                        'credit': values.get('credit', Decimal('0.0')),
                        })

                if balance_prev_id:
                    self.write(balance_prev_id, {
                            'transfer': balance_id,
                            })

        return balance_id

    def post_cancel(self, values=None):
        '''
        Удаление из остатка и оборота в учетном регистре счета
        values = {
                'company':move.company.id,
                'period':period_id,
                'account':line.ct_account.id,
                'analytic':line.ct_party.id,
                'model_ref':move.model_ref,
                'project':move.project.id,
                'debit': line.amount,
                'credit': line.amount,
                }
        '''
        if values == None:
            return False

        if not values.get('balance_id', False):
            self.raise_user_error('balance_account_not_find')

        balance = self.browse(values.get('balance_id'))

        if balance.state =='done':
            self.raise_user_error('balance_account_done')

        self.write(balance.id, {
                        'qdebit': balance.qdebit-values.get('qdebit', 0.0),
                        'debit': balance.debit-values.get('debit', Decimal('0.0')),
                        'qcredit': balance.qcredit-values.get('qcredit', 0.0),
                        'credit': balance.credit-values.get('credit', Decimal('0.0')),
                        })
        if balance.transfer and values.get('transfer',True):
            self.transfer_balance(balance.transfer.id, {
                        'qbalance':balance.qbalance_end,
                        'balance':balance.balance_end,
                        'transfer': values.get('transfer',True)
                        })

        return values.get('balance_id')

BalanceProductFixedAssets()

class BalanceProductIntangibleAssets(ModelSQL, ModelView):
    _name = "ekd.balances.intangible_assets"

    def __init__(self):
        super(BalanceProductIntangibleAssets, self).__init__()

        self._error_messages.update({
            'unknown_direct_account':'Unknow Direct Account for Balance!',
            'balance_account_done': 'Balance Account:%s is Done!',
            'balance_account_not_find': 'Balance Account not find!',
        })

    def post_balance(self, values=None):
        '''
         Изменение остатка и оборота в учетном регистре счета
            values = {'company': ID учетной организации,
                      'period': Дата операции,
                      'account': ID счета,
                      'party': ID организации,
                      'product': ID ТМЦ или услуги,
                      'product_uom': ID Ед.измерения ТМЦ или услуги,
                      'unit_price': ID Цена за единицу ТМЦ или услуги,
                      'quantity': Кол-во,
                      'amount': сумма, }
                      'currency': Валюта поля сумма, }
        '''
        if values == None:
            return False

        if values.get('account_kind', 'balance') == 'off_balance_out':
            balance_id = self.search([
                        ('account','=', values.get('account')),
                        ('party','=',values.get('party')),
                        ('product','=',values.get('product')),
                        ('product_uom','=',values.get('product_uom')),
                        ('unit_price','=',values.get('unit_price')),
                        ], limit=1)
        else:
            balance_id = self.search([
                        ('period','=',values.get('period')),
                        ('account','=', values.get('account')),
                        ('party','=',values.get('party')),
                        ('product','=',values.get('product')),
                        ('product_uom','=',values.get('product_uom')),
                        ('unit_price','=',values.get('unit_price')),
                        ], limit=1)

        if len(balance_id):
            if isinstance(balance_id, list):
                balance_id = balance_id[0]

            balance = self.browse(balance_id)

            if balance.state =='done':
                self.raise_user_error('balance_account_done')

            self.write(balance_id, {
                        'qdebit': balance.qdebit+values.get('qdebit', 0.0),
                        'debit': balance.debit+values.get('debit',Decimal('0.0')),
                        'qcredit': balance.qcredit+values.get('qcredit', 0.0),
                        'credit': balance.credit+values.get('credit',Decimal('0.0')),
                        })
            if balance.transfer and values.get('transfer',True):
                self.transfer_balance(balance.transfer.id, {
                            'qbalance':balance.qbalance_end,
                            'balance':balance.balance_end,
                            'transfer': values.get('transfer',True)
                            })
        else:
            if values.get('account_kind', 'balance') == 'off_balance_out':
                balance_id = self.create({
                        'company': values.get('company'),
                        'account': values.get('account'),
                        'party': values.get('party'),
                        'product': values.get('product'),
                        'product_uom': values.get('product_uom'),
                        'unit_price': values.get('unit_price'),
                        'qbalance': qbalance_prev,
                        'balance': balance_prev,
                        'qdebit': values.get('qdebit', 0.0),
                        'debit': values.get('debit', Decimal('0.0')),
                        'qcredit': values.get('qcredit', 0.0),
                        'credit': values.get('credit', Decimal('0.0')),
                        })
            else:
                period_obj = self.pool.get('ekd.period')
                period_prev = period_obj.search([
                        ('company','=',values.get('company')),
                        ('end_date','<',values.get('date_operation')),
                        ], order=[('end_date','DESC')], limit=1)
                if isinstance(period_prev, list) and period_prev:
                    period_prev = period_prev[0]

                qbalance_prev= Decimal('0.0')
                balance_prev= Decimal('0.0')
                balance_prev_id = self.search([
                        ('period','=', period_prev),
                        ('account','=', values.get('account')),
                        ('party','=',values.get('party')),
                        ('product','=',values.get('product')),
                        ('product_uom','=',values.get('product_uom')),
                        ('unit_price','=',values.get('unit_price')),
                        ], limit=1)
                for bal_prev in self.browse(balance_prev_id):
                    qbalance_prev = bal_prev.qbalance_end
                    balance_prev = bal_prev.balance_end

                balance_id = self.create({
                        'company': values.get('company'),
                        'period': values.get('period'),
                        'account': values.get('account'),
                        'party': values.get('party'),
                        'product': values.get('product'),
                        'product_uom': values.get('product_uom'),
                        'unit_price': values.get('unit_price'),
                        'qbalance': qbalance_prev,
                        'balance': balance_prev,
                        'qdebit': values.get('qdebit', 0.0),
                        'debit': values.get('debit', Decimal('0.0')),
                        'qcredit': values.get('qcredit', 0.0),
                        'credit': values.get('credit', Decimal('0.0')),
                        })

                if balance_prev_id:
                    self.write(balance_prev_id, {
                            'transfer': balance_id,
                            })

        return balance_id

    def post_cancel(self, values=None):
        '''
        Удаление из остатка и оборота в учетном регистре счета
        values = {
                'company':move.company.id,
                'period':period_id,
                'account':line.ct_account.id,
                'analytic':line.ct_party.id,
                'model_ref':move.model_ref,
                'project':move.project.id,
                'debit': line.amount,
                'credit': line.amount,
                }
        '''
        if values == None:
            return False

        if not values.get('balance_id', False):
            self.raise_user_error('balance_account_not_find')

        balance = self.browse(values.get('balance_id'))

        if balance.state =='done':
            self.raise_user_error('balance_account_done')

        self.write(balance.id, {
                        'qdebit': balance.qdebit-values.get('qdebit', 0.0),
                        'debit': balance.debit-values.get('debit', Decimal('0.0')),
                        'qcredit': balance.qcredit-values.get('qcredit', 0.0),
                        'credit': balance.credit-values.get('credit', Decimal('0.0')),
                        })
        if balance.transfer and values.get('transfer',True):
            self.transfer_balance(balance.transfer.id, {
                        'qbalance':balance.qbalance_end,
                        'balance':balance.balance_end,
                        'transfer': values.get('transfer',True)
                        })

        return values.get('balance_id')

BalanceProductIntangibleAssets()

class BalanceProductGoods(ModelSQL, ModelView):
    _name = "ekd.balances.goods"

    def __init__(self):
        super(BalanceProductGoods, self).__init__()

        self._error_messages.update({
            'unknown_direct_account':'Unknow Direct Account for Balance!',
            'balance_account_done': 'Balance Account:%s is Done!',
            'balance_account_not_find': 'Balance Account not find!',
        })

    def change_balance(self, goods_period, values=None, last_period=None, new_period=False):
        balance_obj = self.pool.get('ekd.balances.goods.balance')
        if new_period:
            if values.get('fiscalyear').cost_method == 'average':
                if values.get('qdebit'):
                    return balance_obj.create({
                        'period_product': goods_period.id,
                        #'qbalance': last_period.average.qbalance_end or Decimal('0.0'),
                        #'balance': last_period.average.balance_end or Decimal('0.0'),
                        'qdebit': values.get('qdebit'),
                        'debit':values.get('debit'),
                        })
                else:
                    return balance_obj.create({
                        'period_product': goods_period.id,
                        #'qbalance': last_period.average.qbalance_end or Decimal('0.0'),
                        #'balance': last_period.average.balance_end or Decimal('0.0'),
                        'qcredit': values.get('qcredit'),
                        'credit': values.get('credit'),
                        })
            elif values.get('fiscalyear').cost_method == 'fixed':
                if values.get('qdebit'):
                    return balance_obj.create({
                        'period_product': goods_period.id,
                        'unit_price': values.get('unit_price'),
                        #'qbalance': last_period.average.qbalance_end or Decimal('0.0'),
                        #'balance': last_period.average.balance_end or Decimal('0.0'),
                        'qdebit': values.get('qdebit'),
                        'debit':values.get('debit'),
                        })
                else:
                    return balance_obj.create({
                        'period_product': goods_period.id,
                        'unit_price': values.get('unit_price'),
                        #'qbalance': last_period.average.qbalance_end or Decimal('0.0'),
                        #'balance': last_period.average.balance_end or Decimal('0.0'),
                        'qcredit': values.get('qcredit'),
                        'credit': values.get('credit'),
                        })
            elif values.get('fiscalyear').cost_method == 'fifo':
                raise Exception('Sorry', 'This don t released')
            elif values.get('fiscalyear').cost_method == 'lifo':
                raise Exception('Sorry', 'This don t released')
        else:
            if values.get('fiscalyear').cost_method == 'average':
                if values.get('qdebit'):
                    balance.write(goods_period.balance_average.id, {
                        'qdebit': goods_period.balance_average.qdebit + values.get('qdebit'),
                        'debit': goods_period.balance_average.debit + values.get('debit'),
                        })
                else:
                    balance_obj.write(goods_period.balance_average.id, {
                        'qcredit': goods_period.balance_average.qcredit + values.get('qcredit'),
                        'credit': goods_period.balance_average.credit + values.get('credit'),
                        })
                return goods_period.balance_average.id

            elif values.get('fiscalyear').cost_method == 'fixed':
                for line_fixed in goods_period.period_amounts:
                    if line_fixed.unit_price == values.get('unit_price'):
                        if values.get('qdebit'):
                            #raise Exception(str(values))
                            balance_obj.write(line_fixed.id, {
                                'qdebit': line_fixed.qdebit + values.get('qdebit'),
                                'debit':  line_fixed.debit + values.get('debit'),
                                })
                        else:
                            balance_obj.write(line_fixed.id, {
                                'qcredit': line_fixed.qcredit + values.get('qcredit'),
                                'credit':  line_fixed.credit + values.get('credit'),
                                })
                        #raise Exception(str(values), str(line_fixed.id))
                        return line_fixed.id
                # Если не нашли то создаем
                if values.get('qdebit'):
                    return balance_obj.create({
                        'period_product': goods_period.id,
                        'unit_price': values.get('unit_price'),
                        #'qbalance': last_period.average.qbalance_end or Decimal('0.0'),
                        #'balance': last_period.average.balance_end or Decimal('0.0'),
                        'qdebit': values.get('qdebit'),
                        'debit':values.get('debit'),
                        })
                else:
                    return balance_obj.create({
                        'period_product': goods_period.id,
                        'unit_price': values.get('unit_price'),
                        #'qbalance': last_period.average.qbalance_end or Decimal('0.0'),
                        #'balance': last_period.average.balance_end or Decimal('0.0'),
                        'qcredit': values.get('qcredit'),
                        'credit': values.get('credit'),
                        })

            elif values.get('fiscalyear').cost_method == 'fifo':
                raise Exception('Sorry', 'This don t released')
            elif values.get('fiscalyear').cost_method == 'lifo':
                raise Exception('Sorry', 'This don t released')

    def post_balance(self, values=None):
        '''
        Изменение остатка и оборота в учетном регистре счета
        values = {
                      'period': BrowseRecord(Учетный период)
                      'account': BrowseRecord(ID счета),
                      'analytic': [{
                            'id': ID строки
                            'level': Уровень аналитики,
                            'model_ref': модель и ID,
                                   },...],строк
                      'qdebit': Кол-во,
                      'debit': Сумма,
                      'qcredit': Кол-во, 
                      'credit': Сумма, 
                }
        '''
        if values == None or not values.get('analytic', False):
            return False
        department = False
        product_id = None
        product_uom = None
        unit_price = Decimal('0.0')
        res={}
        for line_analytic in values.get('analytic'):
            model_ref, model_id = line_analytic.get('model_ref').split(',',1)
            if model_ref in [
                'ekd.company.department',
                'ekd.company.department.stock',
                ] and model_id != '0':
                department = int(model_id)
            elif model_ref in [
                'party.party',
                'party.supplier',
                'party.customer',
                'company.employee',
                ]:
                party = int(model_id)
            res[line_analytic.get('id')] = []
        product_id = values.get('product').get('product').id
        product_uom = values.get('product').get('uom').id
        unit_price = values.get('product').get('unit_price')
        #raise Exception('IN', str(values))
        if department:
            goods_id = self.search([
                ('account','=', values.get('account').id),
                ('department','=', department),
                ('party','=', party),
                ('product','=', product_id),
                ('product_uom','=',product_uom),
                ])
            #raise Exception('IN', goods_id, values.get('account').id, department, party, product_id, product_uom)
        else:
            goods_id = self.search([
                ('account','=', values.get('account').id),
                ('party','=', party),
                ('product','=', product_id),
                ('product_uom','=',product_uom),
                ], limit=1)
        #raise Exception(str(goods_id), str(values.get('account').id), str(department), str(party), str(product_id), str(product_uom))

        if goods_id:
            if isinstance(goods_id, list):
                goods_id = goods_id[0]

            goods = self.browse(goods_id)
            if goods.curr_period.period.id == values.get('period').id:
                balance_id = self.change_balance(goods.curr_period, values)
            elif goods.last_period.period.id == values.get('period').id:
                balance_id = self.change_balance(goods.last_period, values)
            elif goods.curr_period.period.end_date < values.get('period').start_date:
                goods_period_obj = self.pool.get('ekd.balances.goods.period')
                curr_period = goods_period_obj.create({
                                        'account': goods.id,
                                        'period': values.get('period').id,
                                        })
                self.write(goods.id, {
                            'last_period': goods.curr_period.id,
                            'curr_period': curr_period,
                            })
                balance_id = self.change_balance(goods.curr_period, values, new_period=True)

            else:
                for goods_period in goods.periods:
                    if goods_period.period.id == values.get('period').id:
                        balance_id = self.change_balance(goods_period, values)
                        break

        else:
            bal_period_obj = self.pool.get('ekd.balances.goods.period')
            balance_obj = self.pool.get('ekd.balances.goods.balance')

            if department:
                goods_id = self.create({
                    'account': values.get('account'),
                    'department': department,
                    'party': party,
                    'product': product_id,
                    'product_uom': product_uom,
                    })
            else:
                goods_id = self.create({
                    'account': values.get('account'),
                    'party': party,
                    'product': product_id,
                    'product_uom': product_uom,
                    })

            bal_period_id = bal_period_obj.create({
                    'account': goods_id,
                    'period': values.get('period').id,
                    })
            self.write(goods_id, {'curr_period':bal_period_id})

            balance_id = self.change_balance(
                                bal_period_obj.browse(bal_period_id),
                                values, new_period=True)

        for res_id in res.keys():
            res[res_id] = [goods_id, balance_id]
        return res

    def post_cancel(self, values=None):
        '''
        Удаление из остатка и оборота в учетном регистре счета
        values = {
                'company':move.company.id,
                'period':period_id,
                'account':line.ct_account.id,
                'analytic':line.ct_party.id,
                'model_ref':move.model_ref,
                'project':move.project.id,
                'debit': line.amount,
                'credit': line.amount,
                }
        '''
        if values == None or not values.get('analytic', False):
            return None
            raise Exception("Don't find analytic %s"%(values))


        balance_ids = ",".join(str(x.ref_period) for x in values.get('analytic'))
        cr = Transaction().cursor
        if values.get('debit') and balance_ids:
            cr.execute("UPDATE ekd_balances_goods_balance "\
                    " SET qdebit = qdebit-%s, debit = debit-%s,"\
                    " write_date='%s' "%(values.get('qdebit'),\
                    values.get('debit'), datetime.datetime.now())+\
                    " WHERE id in ("+balance_ids+")")
        elif values.get('credit') and balance_ids:
            #raise Exception(str(values))
            cr.execute("UPDATE ekd_balances_goods_balance "\
                    " SET qcredit = qcredit-%s, "\
                    " credit = credit-%s, write_date='%s' "%\
                    (values.get('qcredit'),values.get('credit'), datetime.datetime.now())+\
                    " WHERE id in ("+balance_ids+")")
        #else:
        #    raise Exception('Error values', str(values) )

        #if balance.transfer and values.get('transfer',True):
        #    self.transfer_balance(balance.transfer.id, {
        #                'qbalance':balance.qbalance_end,
        #                'balance':balance.balance_end,
        #                'transfer': values.get('transfer',True)
        #                })

        return 

BalanceProductGoods()