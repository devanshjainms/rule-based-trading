"""
YAML Parser for Trading Rules.

This module provides functionality to load, save, and manage trading
rules from YAML configuration files.

:copyright: (c) 2025
:license: MIT
"""

import yaml
from pathlib import Path
from typing import Optional, Union

from .schema import TradingConfig, ExitRule


class RulesParser:
    """
    Load and save trading rules from YAML configuration files.

    This class handles parsing YAML files containing trading rules,
    caching configurations, and detecting file changes for hot-reload.

    :param rules_path: Path to the YAML rules file.
    :type rules_path: Union[str, Path]

    :ivar rules_path: Path object pointing to the rules file.
    :ivar _config: Cached TradingConfig instance.
    :ivar _mtime: Last modification time of the rules file.

    Example::

        parser = RulesParser("rules.yaml")
        config = parser.load()
        for rule in config.rules:
            print(rule.name)
    """

    def __init__(self, rules_path: Union[str, Path] = "rules.yaml") -> None:
        """
        Initialize the RulesParser with a path to the rules file.

        :param rules_path: Path to the YAML rules file. Defaults to "rules.yaml".
        :type rules_path: Union[str, Path]
        """
        self.rules_path = Path(rules_path)
        self._config: Optional[TradingConfig] = None
        self._mtime: Optional[float] = None

    def load(self, reload: bool = False) -> TradingConfig:
        """
        Load rules from the YAML file.

        Uses caching to avoid re-reading unchanged files. The cache is
        invalidated when the file modification time changes.

        :param reload: Force reload even if cached config exists.
        :type reload: bool
        :returns: The loaded trading configuration.
        :rtype: TradingConfig

        Example::

            config = parser.load()
            config = parser.load(reload=True)
        """
        if not self.rules_path.exists():
            self._config = TradingConfig()
            return self._config

        mtime = self.rules_path.stat().st_mtime

        if not reload and self._config and self._mtime == mtime:
            return self._config

        with open(self.rules_path, "r") as f:
            data = yaml.safe_load(f) or {"version": "2.0", "rules": []}

        self._config = TradingConfig(**data)
        self._mtime = mtime
        return self._config

    def save(self, config: Optional[TradingConfig] = None) -> None:
        """
        Save rules to the YAML file.

        :param config: Configuration to save. Uses cached config if None.
        :type config: Optional[TradingConfig]
        :raises ValueError: If no config is provided and no cached config exists.

        Example::

            parser.save(config)
            parser.save()
        """
        config = config or self._config
        if config is None:
            raise ValueError("No config to save")

        data = config.model_dump(exclude_none=True)

        with open(self.rules_path, "w") as f:
            yaml.dump(data, f, default_flow_style=False, sort_keys=False)

        self._mtime = self.rules_path.stat().st_mtime

    def add_rule(self, rule: ExitRule) -> None:
        """
        Add a new rule to the configuration.

        :param rule: The exit rule to add.
        :type rule: ExitRule
        :raises ValueError: If a rule with the same ID already exists.

        Example::

            rule = ExitRule(rule_id="my-rule", name="My Rule", symbol_pattern="NIFTY*")
            parser.add_rule(rule)
        """
        config = self.load()
        if config.get_rule(rule.rule_id):
            raise ValueError(f"Rule '{rule.rule_id}' already exists")
        config.rules.append(rule)
        self.save(config)

    def update_rule(self, rule_id: str, updates: dict) -> ExitRule:
        """
        Update an existing rule with new values.

        :param rule_id: The ID of the rule to update.
        :type rule_id: str
        :param updates: Dictionary of field names and new values.
        :type updates: dict
        :returns: The updated rule.
        :rtype: ExitRule
        :raises ValueError: If the rule is not found.

        Example::

            updated = parser.update_rule("my-rule", {"enabled": False})
        """
        config = self.load()
        rule = config.get_rule(rule_id)
        if rule is None:
            raise ValueError(f"Rule '{rule_id}' not found")

        for key, value in updates.items():
            if hasattr(rule, key):
                setattr(rule, key, value)

        self.save(config)
        return rule

    def delete_rule(self, rule_id: str) -> None:
        """
        Delete a rule from the configuration.

        :param rule_id: The ID of the rule to delete.
        :type rule_id: str

        Example::

            parser.delete_rule("my-rule")
        """
        config = self.load()
        config.rules = [r for r in config.rules if r.rule_id != rule_id]
        self.save(config)

    def reload_if_changed(self) -> bool:
        """
        Reload the configuration if the file has changed.

        Compares the current file modification time with the cached time
        and reloads if different.

        :returns: True if the file was reloaded, False otherwise.
        :rtype: bool

        Example::

            if parser.reload_if_changed():
                print("Rules updated!")
        """
        if not self.rules_path.exists():
            return False
        if self._mtime != self.rules_path.stat().st_mtime:
            self.load(reload=True)
            return True
        return False


_parser: Optional[RulesParser] = None


def get_parser(path: str = "rules.yaml") -> RulesParser:
    """
    Get the default parser instance (singleton pattern).

    Creates a new parser if none exists or if the path has changed.

    :param path: Path to the rules YAML file.
    :type path: str
    :returns: The RulesParser instance.
    :rtype: RulesParser

    Example::

        parser = get_parser()
        parser = get_parser("custom_rules.yaml")
    """
    global _parser
    if _parser is None or str(_parser.rules_path) != path:
        _parser = RulesParser(path)
    return _parser
