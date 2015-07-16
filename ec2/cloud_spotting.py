#!/usr/bin/env python
import boto, datetime, time
import configurator
import cloud_libs as cloud
import boto
import boto.ec2
#import matplotlib.pyplot as plt
import dateutil.parser

from operator import itemgetter

line_types = ['-mo', '-co', '-rd', '-y^', '-b.', '-k*', '-b*', '-go', '-md', '--r*', '-b.', '-y^']
def plot_price_history (history, title):
    figure         = plt.figure()

    region_names   = [x.name for x in boto.ec2.regions()]

    idx = 0
    for region_name in region_names:
        reg_hist   = [ x for x in history if x.region.name == region_name ]
        line       = plt.plot([dateutil.parser.parse(x.timestamp) for x in reg_hist ],
                              [x.price     for x in reg_hist ],  line_types[idx],  label=region_name)
        plt.setp(line, alpha=0.6, antialiased=True, linewidth=2.0)
        idx += 1

    plt.legend(loc=2, ncol=10,  borderaxespad=2)
    plt.ylabel("Price")
    plt.xlabel("Time")
    plt.show()

def price_probability(history, title):

    history = history[::-1]
    total_history = []
    for index in range(0, len(history)-1):
        current_tstamp = dateutil.parser.parse(history[index].timestamp)
        current_price  = history[index].price
        lookahead      = index+1
        duration       = 0;
        #print "{0}".format(current_price)
        while lookahead < len(history)-1 :
            next_tstamp    = dateutil.parser.parse(history[lookahead].timestamp)
            next_price     = history[lookahead].price
            duration       = next_tstamp - current_tstamp;
            #print "     {0} {1}".format(next_price, next_tstamp-current_tstamp)
            if ( next_price > current_price ):
                #print "     {0} {1}".format(next_price, duration)
                #total_history[int(current_price*1000)] = duration;
                total_history.append([current_price, duration])
                break
            lookahead += 1

        #print "="*20

    #for item in sorted(total_history, key=itemgetter(0)):
    #    print item[0], item[1]
    return sorted(total_history, key=itemgetter(0))


def plot_distribution(sorted_history):
    figure         = plt.figure()

    price_dict     = {};
    for item in sorted_history:
        key = item[0]*10000;
        if key not in price_dict:
            price_dict[key] = item[1];
        else:
            price_dict[key] += item[1];

    distrib = []
    for key in price_dict:
        distrib.append([float(key)/10000, price_dict[key].total_seconds()/3600])
        print float(key)/10000, price_dict[key].total_seconds()/3600

    #line       = plt.plot([x[0]  for x in distrib ],
    #                      [x[1]  for x in distrib ],  '-r*',  label="Time at price")
    plt.bar([x[0]  for x in sorted(distrib, key=itemgetter(0)) ],
            [x[1]  for x in sorted(distrib, key=itemgetter(0)) ],  color='r',  label="Time at price")
    #plt.setp(line, alpha=0.6, antialiased=True, linewidth=2.0)

    plt.legend(loc=2, ncol=10,  borderaxespad=2)
    plt.ylabel("Time")
    plt.xlabel("Price")
    plt.show()


def get_spot_prices(conn, configs):
    history      = conn.get_spot_price_history()
    Prices       = {}
    for item in history:
        if item.instance_type not in Prices:
            Prices[item.instance_type] = [];
        Prices[item.instance_type].append(item)
        #Price.append([item.instance_type, item.price, item.region])
        #sprint item.instance_type, item.price, item.region
    return Prices


#configs, conn = cloud.init()
#request       = conn.request_spot_instances(0.2590, configs['WORKER_IMAGE'],
#                                            count=1, type='one-time',
#                                            key_name=configs['AWS_KEYPAIR_NAME'],
#                                            instance_type=configs['WORKER_MACHINE_TYPE'])
#print request
#print dir(request)

#price_hist = conn.get_spot_price_history(instance_type=configs['WORKER_MACHINE_TYPE'])
#price_hist = conn.get_spot_price_history() #instance_type=configs['WORKER_MACHINE_TYPE'])
#print price_hist
#plot_price_history(price_hist, "Price_history")
#sorted_hist = price_probability(price_hist, "Price probabilities")
#plot_distribution(sorted_hist)



