#!/usr/bin/env python3
import argparse, json, os, re
from urllib.request import Request, urlopen
from collections import Counter
from pathlib import Path
import pandas as pd
PATTERN = re.compile(r'^(?P<timestamp>\w{3}\s+\d+\s+\S+)\s+(?P<host>\S+)\s+(?P<service>[\w.-]+)(?:\[\d+\])?:\s+(?P<message>.*)$')
def read_logs(path):
    rows=[]
    for line in path.read_text(errors='replace').splitlines():
        m=PATTERN.match(line)
        if m:
            row=m.groupdict(); msg=row['message'].lower()
            row['level']='error' if any(x in msg for x in ('error','failed','warning')) else 'info'; rows.append(row)
    return pd.DataFrame(rows, columns=['timestamp','host','service','message','level'])
def local_summary(df):
    if df.empty: return '没有解析出有效日志。'
    bad=df[df.level=='error']; top=Counter(bad.service).most_common(3)
    out=[f'共解析 {len(df)} 条日志，其中异常 {len(bad)} 条。']
    if top: out.append('异常最多的服务：'+', '.join(f'{s}({n}条)' for s,n in top)+'。')
    if any(df.message.str.contains('91% full',case=False,na=False)): out.append('发现磁盘空间告警，建议立即检查并清理大文件。')
    if any(df.message.str.contains('failed password',case=False,na=False)): out.append('发现 SSH 登录失败，建议核查来源 IP 并检查登录策略。')
    return ''.join(out)

def ai_summary(df):
    """Ask an OpenAI-compatible API for an operator-friendly diagnosis."""
    key = os.getenv('AI_API_KEY')
    if not key:
        return local_summary(df) + '\n（未设置 AI_API_KEY，当前使用本地规则摘要。）'
    base = os.getenv('AI_BASE_URL', 'https://api.openai.com/v1').rstrip('/')
    model = os.getenv('AI_MODEL', 'gpt-4o-mini')
    evidence = df[df.level == 'error'][['timestamp','service','message']].to_dict('records')
    prompt = ('你是 Linux 运维助手。请根据以下异常日志，用中文输出：1.总体状况；2.可能原因；'
              '3.按优先级排列的排查命令。不要编造日志中没有的事实。\n异常日志：' + json.dumps(evidence, ensure_ascii=False))
    body = json.dumps({'model': model, 'temperature': 0.2,
                       'messages': [{'role':'user','content':prompt}]}).encode()
    req = Request(base + '/chat/completions', data=body,
                  headers={'Authorization':'Bearer '+key, 'Content-Type':'application/json'})
    try:
        with urlopen(req, timeout=30) as response:
            return json.loads(response.read())['choices'][0]['message']['content']
    except Exception as exc:
        return local_summary(df) + f'\n（AI 接口调用失败，已回退本地摘要：{exc}）'
def main():
    ap=argparse.ArgumentParser(description='分析 Linux 日志并生成 Markdown 报告'); ap.add_argument('logfile',type=Path); ap.add_argument('-o','--output',type=Path,default=Path('reports/report.md')); ap.add_argument('--ai',action='store_true',help='调用 OpenAI 兼容接口生成诊断'); a=ap.parse_args()
    df=read_logs(a.logfile); a.output.parent.mkdir(parents=True,exist_ok=True)
    stats=df.groupby(['service','level']).size().rename('count').to_markdown() if not df.empty else '无数据'; errors=df[df.level=='error'].to_markdown(index=False) if not df.empty else '无异常'
    summary=ai_summary(df) if a.ai else local_summary(df)
    report=f'# Linux 日志分析报告\n\n数据源：`{a.logfile}`\n\n## 统计\n\n{stats}\n\n## AI 智能诊断\n\n{summary}\n\n## 关键日志\n\n{errors}\n'; a.output.write_text(report,encoding='utf-8'); print(summary); print(f'报告已写入：{a.output}')
if __name__=='__main__': main()
