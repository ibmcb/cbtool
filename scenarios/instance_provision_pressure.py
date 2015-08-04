#!/usr/bin/python

import itertools
import fnmatch
import json
import os
import pwd
import redis
import prettytable
import datetime

from sys import path, argv, stdout
from time import sleep, time
from optparse import OptionParser

from common import *

class ExpRunner:

    # ##############################################################
    # ##############################################################
    def __init__ (self, options, api):
        self.options      = options
        self.cloud_name   = options.cloud_name
        self.api          = api
        self.cloud_model  = api.cldlist()[0]["model"]
        self.vmc_name     = api.vmclist(self.cloud_name)[0]["name"]
        _cb_dirs = api.cldshow(options.cloud_name, "space")
        self.cb_base_dir = os.path.abspath(_cb_dirs["base_dir"])
        self.cb_data_dir = os.path.abspath(_cb_dirs["data_working_dir"])        
        self.cloud_defs   = ''
        
        if self.cloud_model == "sim" :
            self.options.ift = int(self.options.ift)/10
            self.options.fault_duration = int(self.options.fault_duration)/10
        
    # ##############################################################
    #                   statistics 
    # ##############################################################

    def dumpstats(self, logfp):
        ailist, vmlist = self.diffstats()
        print >>logfp, '%5d %6d %6d %6d %6d' % \
            (time()-self.basetime, 
             ailist[0]+ailist[1]+ailist[2],
             ailist[0]+ailist[1],
             ailist[3]+ailist[1],
             ailist[1])
        logfp.flush()
        print '%5d %6d %6d %6d %6d             \r' % \
            (time()-self.basetime, 
             ailist[0]+ailist[1]+ailist[2],
             ailist[0]+ailist[1],
             ailist[3]+ailist[1],
             ailist[1]),
        stdout.flush()
        return [ ailist, vmlist ]

    # ##############################################################
    # ##############################################################

    def getstats (self):
        vdict = self.api.stats(self.cloud_name)['experiment_counters']
        ai_arrived = int(vdict['AI']['arrived'])
        ai_failed  = int(vdict['AI']['failed'])
        ai_arriving  = int(vdict['AI']['arriving'])
        ai_departed  = int(vdict['AI']['departed'])

        vm_arrived = int(vdict['VM']['arrived'])
        vm_failed  = int(vdict['VM']['failed'])
        vm_arriving  = int(vdict['VM']['arriving'])
        vm_departed  = int(vdict['VM']['departed'])

        ailist = [ai_arrived, ai_failed, ai_arriving, ai_departed]
        vmlist = [vm_arrived, vm_failed, vm_arriving, vm_departed]
        return [ailist, vmlist]

    # ##############################################################
    # ##############################################################

    def diffstats (self):
        if self.baseline:
            ailist, vmlist = self.getstats()
            return [[ailist[0]-self.baseline[0][0], \
                     ailist[1]-self.baseline[0][1], \
                     ailist[2]-self.baseline[0][2], \
                     ailist[3]-self.baseline[0][3]], \
                    [vmlist[0]-self.baseline[1][0], \
                     vmlist[1]-self.baseline[1][1], \
                     vmlist[2]-self.baseline[1][2], \
                     vmlist[3]-self.baseline[1][3]]]
            
    # ##############################################################
    # ##############################################################

    def pressure_experiment(self, logfp, scaling_factor = 1, exp_name = "auto", fake_vms = False):

        _arrival_rate = float(self.options.rate) * scaling_factor
        _size_ai = int(self.options.size_ai)
        _max_ais = float(self.options.max_ais) * scaling_factor
        _max_vms = float(_max_ais * _size_ai)
        _avg_ais = float(self.options.avg_ais) * scaling_factor
        _total_ais = float(self.options.total_ais) * scaling_factor
        
        ai_iait            = float(1.0 / _arrival_rate)
        ai_lifetime        = int (1 + _avg_ais/_arrival_rate)

        _load_duration = int(ai_lifetime/5)

        if exp_name == "auto" :
            exp_name = self.options.experiment_id

        for fp in [stdout, logfp]:
            print >>fp, '#EXPERIMENT ID %s'%(exp_name);
            print >>fp, '#========================================';
            print >>fp, '# PARAM: Target pressure (AI/s) = %f'%(_arrival_rate);
            print >>fp, '# PARAM: VM multiplier          = %d'%(_size_ai);
            print >>fp, '# PARAM: MAX simultaneous AIs   = %d'%(_max_ais);
            print >>fp, '# PARAM: VM simultaneous VMs   = %d'%(_max_vms);            
            print >>fp, '# PARAM: average simult. AIs    = %d'%(_avg_ais);
            print >>fp, '# PARAM: Total AIs to start     = %d'%(_total_ais);
            print >>fp, '# PARAM: VMs are fake           = %d'%(fake_vms);
            print >>fp, '# CALC:  AI IAIT          (s)   = %f'%(ai_iait);
            print >>fp, '# CALC:  AI LIFETIME      (s)   = %d'%(ai_lifetime);
            print >>fp, '# CALC:  AI LOAD DURATION (s)   = %d'%(_load_duration);            
            print >>fp, '# ----'

        # -------------------------------------------------
        # set cloud parameters: maximum simultaneous AIs and VMs
        # -------------------------------------------------
            
        self.api.expid(self.cloud_name, exp_name)
        self.api.cldalter(self.cloud_name, 'admission_control', 
                          'ai_max_reservations', str(_max_ais))
        self.api.cldalter(self.cloud_name, 'admission_control', 
                          'vm_max_reservations', str(_max_vms))

        # -------------------------------------------------
        # this defines how much pressure we put on nova
        # -------------------------------------------------

        self.api.cldalter(self.cloud_name, 'vm_defaults', 
                          'update_attempts', '60')
        self.api.cldalter(self.cloud_name, 'vm_defaults', 
                          'update_frequency', '10')
        self.api.cldalter(self.cloud_name, 'ai_defaults', 
                          'update_attempts', '60')
        self.api.cldalter(self.cloud_name, 'ai_defaults', 
                          'update_frequency', '10')
        self.api.cldalter(self.cloud_name, 'aidrs_defaults',
                          'daemon_parallelism', str(_max_ais))
        self.api.cldalter(self.cloud_name, 'ai_defaults',
                          'attach_parallelism', str(_max_ais))

        # -------------------------------------------------
        # deal with fake VMs (that cannot be tested/checked)
        # and AI
        # -------------------------------------------------
        if fake_vms :
            self.api.cldalter(self.cloud_name, 'vm_defaults', 
                              'check_boot_complete', 'wait_for_0')
            self.api.cldalter(self.cloud_name, 'vm_defaults', 
                              'transfer_files', 'false')
            self.api.cldalter(self.cloud_name, 'vm_defaults', 
                              'run_generic_scripts', 'false')
            self.api.cldalter(self.cloud_name, 'ai_defaults', 
                              'run_application_scripts', 'false')
            self.api.cldalter(self.cloud_name, 'ai_defaults', 
                              'dont_start_load_manager', 'true')
        else:
            if self.cloud_model != "sim" :
                self.api.cldalter(self.cloud_name, 'vm_defaults', 
                                  'check_boot_complete', 'run_command_/bin/true')
                self.api.cldalter(self.cloud_name, 'vm_defaults', 
                                  'transfer_files', 'true')
                self.api.cldalter(self.cloud_name, 'vm_defaults', 
                                  'run_generic_scripts', 'true')
                self.api.cldalter(self.cloud_name, 'ai_defaults', 
                                  'run_application_scripts', 'true')
                self.api.cldalter(self.cloud_name, 'ai_defaults', 
                                  'dont_start_load_manager', 'false')
            else :
                self.api.typealter(self.cloud_name, 'nullworkload', 'app_errors', "0")
                        
        workload_sut="%d_x_tinyvm"%(_size_ai)

        self.api.typealter(self.cloud_name, 'nullworkload', 'sut', workload_sut)
        self.api.patternalter(self.cloud_name, 'simplenw', 'load_duration', str(_load_duration))        
        self.api.patternalter(self.cloud_name, 'simplenw', 'iait', str(ai_iait))
        self.api.patternalter(self.cloud_name, 'simplenw', 'lifetime', str(ai_lifetime))

        # -------------------------------------------------
        #          initialize statistics
        # -------------------------------------------------

        self.baseline = self.getstats()
        self.basetime = time()

        # -------------------------------------------------
        # start experiment: attach submitter
        # -------------------------------------------------

        print '# t=%5d: Starting experiment: waiting for %d AI starts.'%\
            (0, _total_ais)
        self.api.appdrsattach(self.cloud_name, 'simplenw')

        # -------------------------------------------------
        # wait until a set number of AIs have started
        # -------------------------------------------------

        _fault_clock = {}
        _fault_clock["time_to_next_fault"] = int(self.options.ift)        
        _fault_clock["time_to_next_repair"] = 0
                
        while True:
            _fault_clock["loop_start_time"] = time()
            ailist, vmlist = self.dumpstats(logfp)
            ai_started  = ailist[0]+ailist[1]+ailist[2]
            if ai_started >= _total_ais: 
                break
            sleep(5)
            selective_fault_injection(self.options, self.api, _fault_clock)
            
        # -------------------------------------------------
        # detach workload
        # -------------------------------------------------
        _fault_clock["time_to_next_fault"] = int(self.options.ift)                        
        _fault_clock["time_to_next_repair"] = -1
        selective_fault_injection(self.options, self.api, _fault_clock)
            
        print '# t=%5d: All AIs started. Now waiting for arrivals.'% \
            (time()-self.basetime)
        self.api.appdrsdetach(self.cloud_name, 'all')

        # -------------------------------------------------
        # wait for arrivals
        # -------------------------------------------------

        while True:
            ailist, vmlist = self.dumpstats(logfp)
            if ailist[2] == 0: 
                break
            sleep(5)


        t1 = time()
        print '# t=%5d: All AIs arrived. Experiment complete.'%\
            (t1-self.basetime)

        # -------------------------------------------------
        # print results
        # -------------------------------------------------

        ailist, vmlist = self.dumpstats(logfp)
        ai_total    = ailist[0] + ailist[1]
        ai_failrate = 1.0 * ailist[1] / ai_total
        ai_pressure = 1.0 * ai_total/(t1-self.basetime)

        vm_total    = vmlist[0] + vmlist[1]
        vm_failrate = 1.0 * vmlist[1] / vm_total
        vm_pressure = 1.0 * vm_total/(t1-self.basetime)

        for fp in [stdout,logfp]:
            print >>fp,'# ================================';
            print >>fp,'# MEASURED: AI starts         = %5d'%(ai_total);
            print >>fp,'# MEASURED: AI failure rate   = %f'%(ai_failrate);
            print >>fp,'# MEASURED: AI pressure       = %f'%(ai_pressure);
            print >>fp,'# MEASURED: VM starts         = %5d'%(vm_total);
            print >>fp,'# MEASURED: VM failure rate   = %f'%(vm_failrate);
            print >>fp,'# MEASURED: VM pressure       = %f'%(vm_pressure);
            print >>fp,'# ================================'


        _msg = "Experiment \"" + exp_name + "\" ended. Performance metrics will"
        _msg += " be collected in .csv files." 
        print _msg
        _url = self.api.monextract(self.options.cloud_name, "all", "all")

        _msg = "Data is available at url \"" + _url + "\". \nTo automatically generate"
        _msg += " plots, just run \"" + self.cb_base_dir + "/util/plot/cbplotgen.R "
        _msg += "-d " + self.cb_data_dir + " -e " + (exp_name)
        _msg += " -c -p -r -l -a\""
        print _msg
    
        # -------------------------------------------------
        # detach/clean up
        # -------------------------------------------------
        cloud_cleanup(self.options, self.api)

        return

def cli_postional_argument_parser() :
    '''
    TBD
    '''
    
    _usage = "./" + argv[0] + " <cloud_name> <experiment_id> [max ais] [avg ais] [rate] [total ais] [ai size] [fault] [inter-fault time] [fault duration]"

    options, args = cli_named_option_parser()

    if len(argv) < 3 :
        print _usage
        exit(1)

    options.cloud_name = argv[1]

    if len(argv) > 3:
        options.max_ais = argv[3]    
    else :
        options.max_ais = "10"

    if len(argv) > 4:
        options.avg_ais = argv[4]    
    else :
        options.avg_ais = "3"

    if len(argv) > 5:
        options.rate = argv[5]    
    else :
        options.rate = "0.25"

    if len(argv) > 6:
        options.total_ais = argv[6]    
    else :
        options.total_ais = "20"

    if len(argv) > 7:
        options.size_ai = argv[7]    
    else :
        options.size_ai = "1"

    if len(argv) > 8:
        options.fault_situation = argv[8]  
    else :
        options.fault_situation = "nova-api-kp"

    if len(argv) > 9:
        options.ift = argv[9]  
    else :
        options.ift = "300"

    if len(argv) > 10:
        options.fault_duration = argv[10]  
    else :
        options.fault_duration = "60"
        
    options.experiment_id = options.cloud_name + "_pressure_" + options.max_ais + '_' + options.avg_ais + '_' + options.rate + '_' + argv[2]

    print '#' * 5 + " cloud name: " + str(options.cloud_name)
    print '#' * 5 + " max ais: " + str(options.max_ais)    
    print '#' * 5 + " avg ais : " + str(options.avg_ais)
    print '#' * 5 + " rate: " + str(options.rate)
    print '#' * 5 + " total ais: " + str(options.total_ais)
    print '#' * 5 + " size ai: " + str(options.size_ai)
    print '#' * 5 + " fault situation: " + str(options.fault_situation)
    print '#' * 5 + " inter-fault time: " + str(options.ift)
    print '#' * 5 + " fault duration: " + str(options.fault_duration)
            
    return options
    
def main() :
    '''
    TBD
    '''
    _options = cli_postional_argument_parser()    
    _api = connect_to_cb(_options.cloud_name)
    cloud_attach(_options, _api)

    _cb_dirs = _api.cldshow(_options.cloud_name, "space")
    _cb_data_dir = os.path.abspath(_cb_dirs["data_working_dir"])
    exp = ExpRunner(_options, _api)

    _cb_exp_dir = _cb_data_dir + '/' + _options.experiment_id
    if not os.access(_cb_exp_dir, os.F_OK) :
        os.mkdir(_cb_exp_dir)

    _fn = _cb_exp_dir + "/pressure_experiment_history.txt"
    fp = open (_fn, 'w')
    exp.pressure_experiment(fp)
    fp.close()
        
if __name__ == '__main__':
    main()       

exit(0)