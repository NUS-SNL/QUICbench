'''
Utils for parsing experiment config
'''

def get_stack_combi(exp_conf, name):
    for stack_combi in exp_conf["stacks_combinations"]:
        if stack_combi["name"] == name:
            return stack_combi
    return None

def get_port_nos_from_combi(stack_combi):
    port_nos = set()
    for stack in stack_combi["stacks"]:
        port_nos.add(str(stack["port_no"]))
    return port_nos
