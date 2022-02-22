#!/usr/bin/env python

import cherrypy
import html
import machines
import requests
import subprocess

cherrypy.config.update({
    "server.socket_host": "0.0.0.0",
    "server.socket_port": 8000,
})

def html_for_command(command):
    proc = subprocess.run(command, capture_output=True, text=True, shell=True)
    lines = proc.stdout.strip().split("\n")
    html_lines = ["<pre>"] + [html.escape(line) for line in lines] + ["</pre>", ""]
    return "\n".join(html_lines)

GB_LOGS = ["move", "convert", "transfer", "clean"]
BERKELEY_LOGS = ["archive", "turboseti", "events"]


def valid_logs():
    if machines.in_berkeley():
        return BERKELEY_LOGS
    return GB_LOGS


class Status(object):
    @cherrypy.expose
    def status(self, log=None, dc=None):
        if log is None:
            logs = valid_logs()
            parts = ["<h1>bldata pipeline status</h1>"]
            for log in GB_LOGS:
                parts.append(f"<p><a href='?log={log}&dc=gb'>{log}</a></p>")
            for log in BERKELEY_LOGS:
                parts.append(f"<p><a href='?log={log}'>{log}</a></p>")
            return "\n".join(parts)

        if dc == "gb" and machines.in_berkeley():
            # We need to proxy this
            url = f"http://bl-head.gb.nrao.edu:8000/status?log={log}"
            proxies = { "http": "http://klacker:romaniitedomum@proxy.gb.nrao.edu:3128" }
            response = requests.get(url, proxies=proxies)
            return response.text
            
        assert log in valid_logs()
        return html_for_command(f"tail -n 10 /home/obs/logs/{log}*.log")

    
cherrypy.quickstart(Status())
                    
