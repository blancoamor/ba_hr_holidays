import datetime
import math
import time
from operator import attrgetter

from openerp.exceptions import Warning
from openerp import tools
from openerp.osv import fields, osv 
from openerp.tools.translate import _


import logging
_logger = logging.getLogger(__name__)

class hr_holidays(osv.osv):
    _inherit = "hr.holidays"

    
    def onchange_employee(self, cr, uid, ids, employee_id):
        result = super(hr_holidays, self).onchange_employee(cr, uid, ids, employee_id)
        result['value']['section_id'] = False 
        if employee_id:
            employee = self.pool.get('hr.employee').browse(cr, uid, employee_id)
            result['value']['section_id'] = employee.user_id.default_section_id
        return result

    def onchange_date_from(self, cr, uid, ids, date_to, date_from):
        """
        If there are no date set for date_to, automatically set one 8 hours later than
        the date_from.
        Also update the number_of_days.
        """
        # date_to has to be greater than date_from
        if (date_from and date_to) and (date_from > date_to):
            raise osv.except_osv(_('Warning!'),_('The start date must be anterior to the end date.'))

        result = {'value': {}}

        # No date_to set so far: automatically compute one 8 hours later
        if date_from and not date_to:
            date_to_with_delta = datetime.datetime.strptime(date_from, tools.DEFAULT_SERVER_DATETIME_FORMAT) + datetime.timedelta(hours=4.5)
            result['value']['date_to'] = str(date_to_with_delta)

        # Compute and update the number of days
        if (date_to and date_from) and (date_from <= date_to):
            diff_day = self._get_number_of_days(date_from, date_to)
            result['value']['number_of_days_temp'] = round(diff_day,1)
        else:
            result['value']['number_of_days_temp'] = 0

        return result

    def onchange_date_to(self, cr, uid, ids, date_to, date_from):
        """
        Update the number_of_days.
        """

        # date_to has to be greater than date_from
        if (date_from and date_to) and (date_from > date_to):
            raise osv.except_osv(_('Warning!'),_('The start date must be anterior to the end date.'))

        result = {'value': {}}

        # Compute and update the number of days
        if (date_to and date_from) and (date_from <= date_to):
            diff_day = self._get_number_of_days(date_from, date_to)
            result['value']['number_of_days_temp'] = round(diff_day,1)
        else:
            result['value']['number_of_days_temp'] = 0

        return result

    # TODO: can be improved using resource calendar method
    def _get_number_of_days(self, date_from, date_to):
        """Returns a float equals to the timedelta between two dates given as string."""

        DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"
        from_dt = datetime.datetime.strptime(date_from, DATETIME_FORMAT)
        to_dt = datetime.datetime.strptime(date_to, DATETIME_FORMAT)
        timedelta = to_dt - from_dt
        diff_hours = timedelta.days + float(timedelta.seconds) / 3600
        if(diff_hours <= 4 ):
            return 0.5
        if(diff_hours <= 24 ):
            return 1

        diff_day = timedelta.days + float(timedelta.seconds) / 86400
        return math.floor(diff_day)



    _columns = {
        'section_id': fields.many2one('crm.case.section', 'Section'),

    }
    _defaults = {}



class alta_franco_compensatorio(osv.osv_memory):

    _name = 'alta.franco.compensatorio'
    _columns = {
        'section_id': fields.many2one('crm.case.section', 'Section'),
        
        'lunes': fields.many2one('hr.employee', 'lunes'),
        'martes': fields.many2one('hr.employee', 'martes'),
        'miercoles': fields.many2one('hr.employee', 'miercoles'),
        'jueves': fields.many2one('hr.employee', 'jueves'),
        'viernes': fields.many2one('hr.employee', 'viernes'),

        }
    _defaults= {
    }
   

    def set_franco(self, cr, uid,ids,context=None):
        data=self.read(cr, uid, ids[0], ['section_id','lunes', 'martes','miercoles','jueves','viernes',])
        self.set_franco_day(cr, uid,0,data['lunes'], data['section_id'])        
        self.set_franco_day(cr, uid,1,data['martes'], data['section_id'])        
        self.set_franco_day(cr, uid,2,data['miercoles'], data['section_id'])        
        self.set_franco_day(cr, uid,3,data['jueves'], data['section_id'])        
        self.set_franco_day(cr, uid,4,data['viernes'], data['section_id'])        

        dummy, holiday_status_id = self.pool.get('ir.model.data').get_object_reference(cr, uid, 'ba_hr_holidays', 'holiday_status_franco_laboral') 
        dummy, view_id = self.pool.get('ir.model.data').get_object_reference(cr, uid, 'hr_holidays', 'view_holiday_new_calendar') 
        return {
            'name': 'hr_holidays.view_holiday_new_calendar',
            'view_type': 'form',
            'view_mode': 'calendar',
            'res_model': 'hr.holidays',
            'view_id':  view_id ,
            'context': {'search_holiday_status_id':holiday_status_id},
            'type': 'ir.actions.act_window',
            'target': 'current',
        } 

    def set_franco_day(self, cr, uid,day,employee_id, section_id):
        _logger.info('emp %r' , employee_id) 
        if employee_id == False:
            return 

        dummy, holiday_status_id = self.pool.get('ir.model.data').get_object_reference(cr, uid, 'ba_hr_holidays', 'holiday_status_franco_laboral') 


        hr_holidays_obj=self.pool.get('hr.holidays')
        crm_section_obj=self.pool.get('crm.case.section');
        hr_employee_obj=self.pool.get('hr.employee')

        franco_day=self.next_weekday(day)
            

        

        hr_holidays={
            'name': 'Franco laboral',
            'number_of_days_temp' : 0.5 ,
            'date_from': franco_day.strftime("%Y-%m-%d") +  " 11:30:00" ,
            'date_to': franco_day.strftime("%Y-%m-%d") +  " 16:00:00" ,
            'employee_id':employee_id[0],
            'holiday_status_id':holiday_status_id,

        }
        if section_id :
            section_id['section_id']=section_id[0]

        hr_holidays_obj.create(cr, uid,hr_holidays)

    def next_weekday(self , weekday):
        d=datetime.datetime.today()        
        days_ahead = weekday - d.weekday()
        #if days_ahead <= 0: # Target day already happened this week
        days_ahead += 7
        return d + datetime.timedelta(days_ahead)