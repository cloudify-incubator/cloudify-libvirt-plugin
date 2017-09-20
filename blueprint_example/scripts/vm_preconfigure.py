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

    disks = ctx.source.instance.runtime_properties["params"]['disks']

    disks.append({
        'name': 'ide-0-0-0-0',
        'bus': 'ide',
        'dev': 'hda',
        'file': ctx.target.instance.runtime_properties.get('vm_image'),
        'address': {
            'bus': 0,
            'controller': 0,
            'target': 0,
            'unit': 0
        },
        'type': 'qcow2'
    })

    ctx.logger.info(repr(ctx.source.instance.runtime_properties))
    ctx.source.instance.runtime_properties._set_changed()
