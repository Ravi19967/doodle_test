## Setup instructions
* Keep source code in doodle_test folder in root directory of user
* Execute `bash run_solution.sh`
* logs folder in `src` gets updated with every run based on latest data. Ideal solution should be logging ELK (as it scales linearly with new logs)

## Approach
* Setup a topic `user_events` and `event_metrics` with single partition and replica
* Performed data transformations in `etl_app` docker container
* There were 2 possible options to solve the problem. First one was to read all data in parallel proccesses based topic partition and dump the aggregated data to `event_metrics` all together. Second one was to read all data together and aggregate it on the fly and dump it in `event_metrics`. 
    * The first approach was faster but it would result in all records being availabe after some time which makes sense if input events are not sorted. 
    * The second approach leverages the fact that records are sorted and max latency is 5 seconds. This results in faster dumping of data as new user data starts flying in within few moments of starting the process but overall process will be slower.
    * Since the ask was to return results as fast as possible I went with the second approach
* Here in to solve the count distinct problem I used `hashmap` which is implemented using `dict`. I stored all `uids` in a set which does read/write operations in amortize O(1) time. To reduce memory footprint after `65 seconds` of first record of a particutar minute's timestamp. I aggregate the and delete the `uids` which ensures low memory consumption.
* Using set we ensure `99.9% accuracy` in count distinct of `uids`. The memory constraint will grow linearly with `# of distinct users` beyond a certain threshold hosting this code might become costly. So another alternative is `HyperLogLog` algorithm which does this process with around 1% error but in around 1% memory.
* The inital version of code took around `~78 seconds`. The top major bottlenecks were `deserialization` and `reading data from topic`. These bottlenecks were identifed using cProfiler which a deterministic profiler which is good for local but shouldn't be used on production as it has huge overhead cost. For production environment any statistical profiler should be used instead.
    * `deserialization`: To solve this problem what we could have done is make it concurrent and parallel but since design constraints (and GIL) didn't allow it with the present approach. I went the route of faster deserializer. `ujson` is a python package which is around 3 times faster than normal `json` package. This dastrically reduced the running time.
    * `reading data from topic`: There are multiple python kafka clients written in java, c and python. The most performant one based online github report of activision team was `confluent-kafka` as it was a wrapper around C code. In my experience it gave us around 1.5 times faster reads.
* After solving all of these problems the running time was reduced to `~29 seconds`. The memory profiler (`memory-profiler`) also showed that I was using around `125 MiB` at peak time. So I was able to optimize for time and space complexity.
* In a nutshell, the final performance metrics were as follows. All these files are present in the git repo as well:
    * Processed `1000000 Frames` in `28.73 seconds`
    * `33.18 MB/s`
    * `34802.22 Frames/s`
* For `deserialization` aspect of things. I think `AVRO` is a better format over json. As it has one to one support for JSONs. Since Row Indexed format. It supports faster reads as well as giving us the smae benefits of json in the form schema evolution. It also reduces the size of the data packet. I think `AVRO` is the idea format for these operations.
* For `scalabilty` aspect of things. This solution should scale up until around 204.000 Frames per minute beyond which it would always lag. In a scenario of more than 204.000 per minute we should partition the data based on user demographics and go to the other approach. Another approach would be to partition the data on timestamp wherein one minute of data is one one partition and another minutes data on another partition and multiprocessing of data based on multiple consumers in a single consumer group.