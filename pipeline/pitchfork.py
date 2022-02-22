#!/usr/bin/env python

import cherrypy
import html
import jinja2
import subprocess

import plot

cherrypy.config.update({
    "server.socket_port": 7777,
    "server.thread_pool": 1,
})

env = jinja2.Environment(
    loader=jinja2.FileSystemLoader("./templates"),
    autoescape=jinja2.select_autoescape()
)

class Pitchfork(object):
    def __init__(self):
        find_cmd = ["find", "/home/obs/events", "-name", "*.csv"]
        proc = subprocess.run(find_cmd, capture_output=True, text=True)
        event_dirs = [line.rsplit("/", 1)[0] for line in proc.stdout.strip().split("\n")]
        self.cfpairs = []
        for event_dir in event_dirs:
            parts = event_dir.strip("/").split("/")
            self.cfpairs.append(tuple(parts[-2:]))
        print(f"we have candidate events for {len(self.cfpairs)} cadence-frequency pairs")

        
    @cherrypy.expose
    def index(self):
        temp = env.get_template("index.html")
        return temp.render(cfpairs=self.cfpairs)

    @cherrypy.popargs("cadence")
    @cherrypy.popargs("freq")
    @cherrypy.expose
    def events(self, cadence, freq):
        i = self.cfpairs.index((cadence, freq))
        if i == 0:
            prev_url = None
        else:
            pair = self.cfpairs[i - 1]
            prev_url = f"/events/{pair[0]}/{pair[1]}"
        if i == len(self.cfpairs) - 1:
            next_url = None
        else:
            pair = self.cfpairs[i + 1]
            next_url = f"/events/{pair[0]}/{pair[1]}"
            
        temp = env.get_template("events.html")
        event_dir = f"/home/obs/events/{cadence}/{freq}"
        csv = plot.read_csv(event_dir)
        num_events = len(csv)
        return temp.render(cadence=cadence, freq=freq, prev_url=prev_url, next_url=next_url, num_events=num_events)


    @cherrypy.popargs("cadence")
    @cherrypy.popargs("freq")
    @cherrypy.popargs("index")
    @cherrypy.expose
    def png(self, cadence, freq, index):
        index = int(index)
        event_dir = f"/home/obs/events/{cadence}/{freq}"
        buf = plot.plot_event_png(event_dir, index)
        cherrypy.response.headers["Content-Type"]= "image/png"
        buf.seek(0)
        return cherrypy.lib.file_generator(buf)

    
cherrypy.quickstart(Pitchfork())
                    
