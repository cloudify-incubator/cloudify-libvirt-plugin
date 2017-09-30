from cloudify import ctx

if __name__ == "__main__":
    ctx.logger.info("Connect disk to VM")
    ctx.logger.info('From: {} format {}.'.format(
        repr(ctx.source.instance.id),
        repr(ctx.target.instance.id)
    ))

    if "params" not in ctx.source.instance.runtime_properties:
        ctx.source.instance.runtime_properties["params"] = {}

    if "disks" not in ctx.source.instance.runtime_properties["params"]:
        ctx.source.instance.runtime_properties["params"]['disks'] = []

    # hack for cleanup if we install/uninstall several times.
    ctx.source.instance.runtime_properties["params"]['disks'] = []

    disks = ctx.source.instance.runtime_properties["params"]['disks']

    disks.append({
        'bus': 'ide',
        'dev': 'hda',
        'file': ctx.target.instance.runtime_properties.get('vm_image'),
        'type': 'qcow2'
    })

    disks.append({
        'bus': 'ide',
        'dev': 'hdb',
        'file': ctx.target.instance.runtime_properties.get('vm_cloudinit'),
        'type': 'raw'
    })

    ctx.logger.info(repr(ctx.source.instance.runtime_properties))
    ctx.source.instance.runtime_properties._set_changed()
