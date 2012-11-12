def metric_handler(name):  
    try:
        res = open('/proc/cpuinfo').read().count('processor\t:')

        if res > 0:
            return res
    except IOError:
        pass
    return 0 

def metric_init(params):
    print '[cores] number of cores'
    print params

    d1 = {'name': 'cores',
        'call_back': metric_handler,
        'time_max': 60,
        'value_type': 'int',
        'units': 'processors',
        'slope': 'both',
        'format': '%d',
	'groups': 'cpu',
        'description': 'Number of CPUs or virtual CPUs'}

    descriptors = [d1]

    return descriptors

def metric_cleanup():
    '''Clean up the metric module.'''
    pass

#This code is for debugging and unit testing
if __name__ == '__main__':
    metric_init({})
    for d in descriptors:
        v = d['call_back'](d['name'])
        print 'value for %s is %u' % (d['name'],  v)
