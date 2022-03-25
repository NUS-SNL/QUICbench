
def get_remote_cmd(remote_hostname, cmd):
    return ["ssh", remote_hostname, " ".join(cmd)]
