"""
Shader node graph tools: list, add, connect, remove nodes, set node input values.
"""

from __future__ import annotations

import logging

import bpy

from ._helpers import run_tool

logger = logging.getLogger(__name__)


def register(mcp) -> None:
    """Register all shader node tools onto the FastMCP instance."""

    @mcp.tool()
    async def list_shader_nodes(material_name: str) -> str:
        """List all nodes in a material's shader node tree, including their sockets."""

        def _do():
            if not material_name:
                raise ValueError("material_name must not be empty")
            mat = bpy.data.materials.get(material_name)
            if mat is None:
                raise ValueError(f"Material '{material_name}' not found")
            if not mat.use_nodes:
                raise ValueError(f"Material '{material_name}' does not use nodes")
            return [
                {
                    "name": n.name,
                    "type": n.type,
                    "location": [n.location.x, n.location.y],
                    "inputs": [{"name": i.name, "type": i.type} for i in n.inputs],
                    "outputs": [{"name": o.name, "type": o.type} for o in n.outputs],
                }
                for n in mat.node_tree.nodes
            ]

        return await run_tool("list_shader_nodes", _do)

    @mcp.tool()
    async def add_shader_node(
        material_name: str,
        node_type: str,
        location: list[float] = [0.0, 0.0],  # noqa: B006
    ) -> str:
        """Add a new shader node to a material's node tree.

        node_type is a Blender node type string, e.g. 'ShaderNodeTexImage',
        'ShaderNodeMixRGB', 'ShaderNodeTexChecker'.
        """

        def _do():
            if not material_name:
                raise ValueError("material_name must not be empty")
            if not node_type:
                raise ValueError("node_type must not be empty")
            if len(location) != 2:
                raise ValueError("location must have 2 components [x, y]")
            mat = bpy.data.materials.get(material_name)
            if mat is None:
                raise ValueError(f"Material '{material_name}' not found")
            if not mat.use_nodes:
                mat.use_nodes = True
            node = mat.node_tree.nodes.new(type=node_type)
            node.location = tuple(location)
            return {"name": node.name, "type": node.type, "location": list(node.location)}

        return await run_tool("add_shader_node", _do)

    @mcp.tool()
    async def connect_nodes(
        material_name: str,
        from_node: str,
        from_output: str,
        to_node: str,
        to_input: str,
    ) -> str:
        """Connect an output socket of one node to an input socket of another.

        from_output and to_input accept either a socket name (string) or a
        zero-based integer index given as a string (e.g. '0').
        """

        def _do():
            if not material_name:
                raise ValueError("material_name must not be empty")
            mat = bpy.data.materials.get(material_name)
            if mat is None:
                raise ValueError(f"Material '{material_name}' not found")
            if not mat.use_nodes:
                raise ValueError(f"Material '{material_name}' does not use nodes")
            nt = mat.node_tree
            src = nt.nodes.get(from_node)
            if src is None:
                raise ValueError(f"Node '{from_node}' not found in '{material_name}'")
            dst = nt.nodes.get(to_node)
            if dst is None:
                raise ValueError(f"Node '{to_node}' not found in '{material_name}'")

            if from_output.isdigit():
                idx = int(from_output)
                if idx >= len(src.outputs):
                    raise ValueError(
                        f"Output index {idx} out of range for node '{from_node}'"
                    )
                out_socket = src.outputs[idx]
            else:
                out_socket = src.outputs.get(from_output)
                if out_socket is None:
                    raise ValueError(
                        f"Output '{from_output}' not found on node '{from_node}'"
                    )

            if to_input.isdigit():
                idx = int(to_input)
                if idx >= len(dst.inputs):
                    raise ValueError(
                        f"Input index {idx} out of range for node '{to_node}'"
                    )
                in_socket = dst.inputs[idx]
            else:
                in_socket = dst.inputs.get(to_input)
                if in_socket is None:
                    raise ValueError(
                        f"Input '{to_input}' not found on node '{to_node}'"
                    )

            nt.links.new(out_socket, in_socket)
            return {
                "from": f"{from_node}.{from_output}",
                "to": f"{to_node}.{to_input}",
            }

        return await run_tool("connect_nodes", _do)

    @mcp.tool()
    async def remove_node(material_name: str, node_name: str) -> str:
        """Remove a node from a material's shader node tree by name."""

        def _do():
            if not material_name:
                raise ValueError("material_name must not be empty")
            if not node_name:
                raise ValueError("node_name must not be empty")
            mat = bpy.data.materials.get(material_name)
            if mat is None:
                raise ValueError(f"Material '{material_name}' not found")
            if not mat.use_nodes:
                raise ValueError(f"Material '{material_name}' does not use nodes")
            node = mat.node_tree.nodes.get(node_name)
            if node is None:
                raise ValueError(f"Node '{node_name}' not found in '{material_name}'")
            mat.node_tree.nodes.remove(node)
            return {"removed": node_name, "material": material_name}

        return await run_tool("remove_node", _do)

    @mcp.tool()
    async def set_node_value(
        material_name: str,
        node_name: str,
        input_name: str,
        value: float | int | list[float],
    ) -> str:
        """Set the default value of a node's input socket.

        value is a float or int for scalar inputs, or a list[float] for vector/color inputs.
        """

        def _do():
            if not material_name:
                raise ValueError("material_name must not be empty")
            if not node_name:
                raise ValueError("node_name must not be empty")
            if not input_name:
                raise ValueError("input_name must not be empty")
            mat = bpy.data.materials.get(material_name)
            if mat is None:
                raise ValueError(f"Material '{material_name}' not found")
            if not mat.use_nodes:
                raise ValueError(f"Material '{material_name}' does not use nodes")
            node = mat.node_tree.nodes.get(node_name)
            if node is None:
                raise ValueError(f"Node '{node_name}' not found in '{material_name}'")
            socket = node.inputs.get(input_name)
            if socket is None:
                raise ValueError(f"Input '{input_name}' not found on node '{node_name}'")
            socket.default_value = value
            return {"node": node_name, "input": input_name, "value": value}

        return await run_tool("set_node_value", _do)
