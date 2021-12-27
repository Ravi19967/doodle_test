from confluent_kafka import Consumer, Producer

import ujson 
import sys

broker = 'kafka:9093'
consumer_group_id = 'distinct_users'
input_topic = 'user_events'
output_topic = 'event_metrics'

dict_uids = {}
dict_count = {}
processed_dates = set()

def read_data_init():
    consumer_conf = {'bootstrap.servers':  broker,
                        'group.id': consumer_group_id,
                        'auto.offset.reset': "earliest",
                        'enable.auto.commit': True}
    consumer = Consumer(consumer_conf)
    consumer.subscribe([input_topic])
    return consumer

def write_data_init():
    producer_conf = {'bootstrap.servers':  broker}
    producer = Producer(producer_conf)
    return producer

def delivery_report(err, msg):
    if err is not None:
        print('Message delivery failed: {}'.format(err))
    else:
        print('Message delivered to {} [{}]'.format(msg.topic(), msg.partition()))


def calculate_thoughput(timing, n_messages=1000000, msg_size=100):
    print("Processed {0} messsages in {1:.2f} seconds".format(n_messages, timing))
    print("{0:.2f} MB/s".format((msg_size * n_messages) / timing / (1024*1024)))
    print("{0:.2f} Msgs/s".format(n_messages / timing))

def data_flow(message_counter = 0, input_size = 0):
    consumer = read_data_init()
    producer = write_data_init()
    try:
        while True:
            msg = consumer.poll(1.0)
            if msg is None:
                break
            message_counter += 1
            input_json = ujson.loads(msg.value())
            input_size += sys.getsizeof(input_json)
            dict_uids.setdefault(input_json['ts']//60 * 60, set()).add(input_json['uid'])
            if ((input_json['ts']//60 * 60) - 60 not in processed_dates) and ((input_json['ts']//60 * 60)-60 in dict_uids) and (input_json['ts'] > (input_json['ts']//60 * 60) + 5):
                dict_count[(input_json['ts']//60 * 60) - 60]= len(dict_uids[(input_json['ts']//60 * 60)-60])
                producer.poll(0)
                output = {}
                output[(input_json['ts']//60 * 60) - 60] = dict_count[(input_json['ts']//60 * 60) - 60]
                data = ujson.dumps(output)
                producer.produce(output_topic, data.encode('utf-8'), callback=delivery_report)
                processed_dates.add((input_json['ts']//60 * 60) - 60)
                del dict_uids[(input_json['ts']//60 * 60) - 60]
            
    except Exception as e:
        consumer.close()
        producer.flush()
        raise Exception(e)
    
    for key in dict_uids.keys():
        dict_count[key]= len(dict_uids[key])
        output = {}
        output[(input_json['ts']//60 * 60) - 60] = dict_count[(input_json['ts']//60 * 60) - 60]
        data = ujson.dumps(output)
        producer.produce(output_topic, data.encode('utf-8'), callback=delivery_report)

    consumer.close()
    producer.flush()
    return message_counter,input_size

def throughtput_calculator():
    import time
    start = time.time()
    msg, size = data_flow()
    end = time.time() - start
    msg_size = (size / msg) if msg else 0
    sys.stdout = open('code/logs/performance_metrics.log', 'w')
    calculate_thoughput(end,msg,msg_size)
    sys.stdout.close()

if __name__=="__main__":
    throughtput_calculator()