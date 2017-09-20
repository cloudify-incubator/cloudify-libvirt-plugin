from cloudify import ctx

if __name__ == "__main__":
    ctx.logger.info("link")
    vm_id = ctx.source.instance.runtime_properties.get('resource_id')
    resource_id = ctx.target.instance.runtime_properties.get('resource_id')
    ctx.logger.info('Network: ' + repr(resource_id) + ' to VM: ' + repr(vm_id) + ' .')
