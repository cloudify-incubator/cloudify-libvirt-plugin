from cloudify import ctx
import time

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
        'bus': 'scsi',
        'dev': 'sda',
        'file': ctx.target.instance.runtime_properties.get('vm_image'),
        'type': 'qcow2'
    })

    disks.append({
        'bus': 'scsi',
        'dev': 'sdb',
        'file': ctx.target.instance.runtime_properties.get('vm_cloudinit'),
        'type': 'raw'
    })

    networks = ctx.source.instance.runtime_properties["params"].get('networks')
    for network in networks:
        if not network.get('type'):
            network['type'] = "virtio"
        if not network.get('mac'):
            octet_full = (time.time() * 1000) % (256 * 256 * 256)
            octet_low = octet_full / 256
            octet_hi = octet_low / 256
            network['mac'] = "52:54:00:%02x:%02x:%02x" % (
                                octet_low % 256,
                                octet_hi % 256,
                                octet_full % 256,
                            )

    ctx.source.instance.runtime_properties["params"]['networks'] = networks

    ctx.logger.info(repr(ctx.source.instance.runtime_properties))
    ctx.source.instance.runtime_properties._set_changed()
