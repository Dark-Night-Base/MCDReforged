"""
Handling MCDR commands
"""
from typing import TYPE_CHECKING, Dict, List

import mcdreforged.command.builder.command_builder_util as utils
from mcdreforged.command.builder.exception import CommandError
from mcdreforged.command.command_source import CommandSource
from mcdreforged.plugin.plugin_registry import PluginCommandNode
from mcdreforged.utils import string_util
from mcdreforged.utils.logger import DebugOption

if TYPE_CHECKING:
	from mcdreforged.mcdr_server import MCDReforgedServer


# deal with !!MCDR and !!help command
class CommandManager:
	def __init__(self, mcdr_server: 'MCDReforgedServer'):
		self.mcdr_server = mcdr_server
		self.logger = self.mcdr_server.logger
		self.tr = self.mcdr_server.tr
		self.root_nodes = {}  # type: Dict[str, List[PluginCommandNode]]

		self.__preserve_command_error_display_flag = False

	def clear_command(self):
		self.root_nodes.clear()

	def register_command(self, plugin_node: PluginCommandNode):
		for literal in plugin_node.node.literals:
			nodes = self.root_nodes.get(literal, [])
			nodes.append(plugin_node)
			self.root_nodes[literal] = nodes

	def execute_command(self, source: CommandSource, command: str):
		first_literal_element = utils.get_element(command)
		plugin_root_nodes = self.root_nodes.get(first_literal_element, [])
		if len(plugin_root_nodes) > 0 and source.is_console:
			# If this is a command, don't send it towards the server if it's from console input
			source.get_info().cancel_send_to_server()

		command_errors = []
		for plugin_root_node in plugin_root_nodes:
			plugin = plugin_root_node.plugin
			node = plugin_root_node.node
			with self.mcdr_server.plugin_manager.with_plugin_context(plugin):
				try:
					node.execute(source, command)
				except CommandError as e:
					command_errors.append(e)
				except:
					self.logger.exception('Error when executing command "{}" with command source "{}" on {} registered by {}'.format(command, source, node, plugin))
		for error in command_errors:
			if not error.is_handled():
				translation_key = 'command_exception.{}'.format(string_util.hump_to_underline(type(error).__name__))
				try:
					error.set_translated_message(translation_key, lambda key, args: self.mcdr_server.tr(key, *args, allow_failure=False))
				except KeyError:
					self.logger.debug('Fail to translated command error with key {}'.format(translation_key), option=DebugOption.COMMAND)
				source.reply(error.to_mc_color_text())