#!python3
# vim: set ft=python

from f5.bigip import ManagementRoot
from tabulate import tabulate
import click
import time
import os
import yaml
import pprint

try: 
    c = yaml.load(open("bigip.yaml"), Loader=yaml.FullLoader) 
    config = c['hosts'].get(c.get('current'))
    mgmt = ManagementRoot( config['host'] , config['user'], config['password'] )
except:
    click.secho("Unable to login to {}".format(os.environ['BIGIP_HOST']), fg="red")
    raise click.Abort()

def get_pools(ctx, args, incomplete):
    try:
        global mgmt
        return [ pool.name for pool in mgmt.tm.ltm.pools.get_collection() if incomplete in pool.name ] 
    except:
        pass

def get_members(ctx, args, incomplete):
    try:
        global mgmt
        pool = args[args.index("--pool")+1]
        return [ member.name for member in mgmt.tm.ltm.pools.pool.load(name=pool, partition='Common').members_s.get_collection() 
                if incomplete in member.name and member.state == "up" ]
    except:
        pass

def get_contexts(ctx, args, incomplete):
    try:
        c = yaml.load(open("bigip.yaml"), Loader=yaml.FullLoader) 
        available_contexts = c['hosts'].keys()
        return available_contexts
    except:
        pass


@click.group()
@click.option('--partition', type=click.STRING, default='Common')
@click.option('--pool', type=click.STRING, autocompletion=get_pools)
@click.option('--verbose/--noverbose','-v/-V') 
@click.pass_context
def cli(ctx, partition, pool, verbose ):
    """ CLI tool for F5 BIGIP Devices """
    global mgmt
    ctx.ensure_object(dict)
    ctx.obj['verbose'] = verbose
    ctx.obj['mgmt'] = mgmt
    if pool:
        ctx.obj['pool'] = ctx.obj['mgmt'].tm.ltm.pools.pool.load(name=pool, partition='Common')

@cli.group()
def pool():
    pass

@cli.group()
def member():
    pass

@cli.group()
def config():
    pass

@config.command()
@click.argument('context', type=click.STRING, autocompletion=get_contexts)
def context(context):
    c = yaml.load(open("bigip.yaml"), Loader=yaml.FullLoader) 
    available_contexts = c['hosts'].keys()
    if context not in available_contexts:
        click.secho("context {} not found".format(context), fg="red")
        click.Abort()
    c['current'] == context
    with open('bigip.yaml', 'w') as outfile:
        yaml.dump(c, outfile, default_flow_style=False)

    

@pool.command(name="list")
@click.pass_context
def pools_list(ctx):
    for pool in ctx.obj['mgmt'].tm.ltm.pools.get_collection(): 
        if ctx.obj['verbose']: 
            print(pool.raw)
        else:
            print( pool.name ) 

@pool.command(name="stats")
@click.argument("pool_name",type=click.STRING, autocompletion=get_pools)
@click.pass_context
def pools_stats(ctx, pool_name):
    pool = ctx.obj['mgmt'].tm.ltm.pools.pool.load(name=pool_name, partition='Common')
    print(pool.stats.entries.curSessions.value)


@member.command(name='stats')
@click.argument('member_name', type=click.STRING, default="", autocompletion=get_members)
@click.option('--all/--noall','show_all')
@click.pass_context
def members_stats(ctx, member_name, show_all):
    stats = list()
    for member in  ctx.obj['pool'].members_s.get_collection():
        if ((member_name in member.name) or (member_name.lower() == "all")) and  (member.state=="up" or show_all):
            values = { metric.split(".")[1] : value.get("value",0) 
                       for (metric, value) in member.stats.load().raw['entries'].items() 
                       if metric.startswith("serverside") }
            stats.append ( { "member": member.name, **values } )
    print( tabulate( stats, headers="keys"))


@member.command(name='restart')
@click.pass_context
def members_watch(ctx, member_name, counter_name):
    for member in  ctx.obj['pool'].members_s.get_collection():
        if ((member_name in member.name) or (member_name.lower() == "all")) and  member.state=="up":
            if counter_name:
                print ( member.name, end=": " )
                pprint.pprint(member.stats.load().raw['entries'].get(counter_name,{}).get("value", None))
            else:
                pprint.pprint(member.stats.load().raw['entries'])

@member.command(name='list')
@click.pass_context
def members_list(ctx):
    for member in  ctx.obj['pool'].members_s.get_collection():
        click.secho( "{name} [{state}]".format(**member.to_dict()), 
                     fg={ 'up': 'green', 'down': 'red' }.get(member.state))


@member.command(name="disable")
@click.argument("member",type=click.STRING, autocompletion=get_members)
@click.option("--wait/--nowait", default=False)
@click.pass_context
def member_disable(ctx,member, wait):
    if not member in [ m.name for m in ctx.obj['pool'].members_s.get_collection()]:
        print ("Member {} on pool {} not found".format(member, ctx.obj['pool'].name))
        raise click.Abort()
    else:
        print ("Member {} on pool {} disabled".format(member, ctx.obj['pool'].name))


if __name__=="__main__":
    cli()
