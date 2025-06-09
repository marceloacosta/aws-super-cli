#!/usr/bin/env python3
"""
Regression test suite for AWS Super CLI
Tests for specific bugs and issues that have been fixed
"""

import pytest
from typer.testing import CliRunner
from aws_super_cli.cli import app
from unittest.mock import patch


class TestRegressionIssues:
    """Tests for specific regression issues that have been fixed"""
    
    def setup_method(self):
        """Setup for each test"""
        self.runner = CliRunner()
    
    def test_rich_markup_literal_display_bug(self):
        """
        REGRESSION TEST: Rich markup showing as literal text instead of colors
        
        Issue: help command was using print() instead of rprint(), causing 
        Rich markup like [cyan] and [bold] to show as literal text
        
        Fix: Changed print() to rprint() in help command
        """
        result = self.runner.invoke(app, ["help"])
        
        # Verify fix: should NOT contain literal markup tags
        assert "[cyan]" not in result.stdout, "Rich markup should be rendered, not shown literally"
        assert "[bold]" not in result.stdout, "Rich markup should be rendered, not shown literally"
        assert "[/cyan]" not in result.stdout, "Closing tags should not appear literally"
        assert "[/bold]" not in result.stdout, "Closing tags should not appear literally"
        
        # Should still contain the actual content
        assert "AWS Super CLI" in result.stdout
        assert "Most Common Commands:" in result.stdout
    
    def test_empty_error_box_issue(self):
        """
        REGRESSION TEST: Empty error box appearing on CLI help
        
        Issue: Running 'aws-super-cli' without args showed empty error box
        Fixed: Now shows helpful quick reference guide instead of just usage
        """
        result = self.runner.invoke(app, [])
        
        # Should show helpful content (new behavior is better than just "Usage:")
        assert "AWS Super CLI - Quick Reference" in result.stdout
        assert "Most Common Commands:" in result.stdout
        assert "aws-super-cli" in result.stdout
        
        # Exit code 0 is expected for helpful content
        assert result.exit_code == 0
    
    def test_messy_help_text_cleanup(self):
        """
        REGRESSION TEST: Messy help text with examples and hashtags
        
        Issue: Main CLI help had verbose multi-line help with hashtags
        Fix: Simplified to clean single-line description
        """
        result = self.runner.invoke(app, ["-h"])
        
        # Should NOT contain the old messy format
        assert "Quick examples:" not in result.stdout
        assert "Common use cases:" not in result.stdout
        assert "# List EC2 instances" not in result.stdout
        
        # Should contain clean description
        assert "AWS Super CLI" in result.stdout
        assert "resource discovery and security tool" in result.stdout
    
    def test_help_vs_explicit_help_consistency(self):
        """
        REGRESSION TEST: Ensure -h and help command are both clean
        
        Both should provide clean, consistent output
        """
        help_flag_result = self.runner.invoke(app, ["-h"])
        help_cmd_result = self.runner.invoke(app, ["help"])
        
        # Both should succeed
        assert help_flag_result.exit_code == 0
        assert help_cmd_result.exit_code == 0
        
        # Both should contain clean output
        assert "AWS Super CLI" in help_flag_result.stdout
        assert "AWS Super CLI" in help_cmd_result.stdout
        
        # Neither should have markup leakage
        assert "[cyan]" not in help_flag_result.stdout
        assert "[cyan]" not in help_cmd_result.stdout
    
    def test_service_alias_recognition(self):
        """
        REGRESSION TEST: Service aliases should work correctly
        
        Ensure commands like 'ls instances' work as aliases
        """
        # This would normally require AWS mocking, but we can test the message
        result = self.runner.invoke(app, ["ls", "instances"])
        
        # Should recognize alias and show interpretation message
        assert "Interpreting 'instances' as 'ec2'" in result.stdout
    
    def test_graceful_invalid_service_handling(self):
        """
        REGRESSION TEST: Invalid service names should be handled gracefully
        
        Should show helpful suggestions, not crash
        """
        result = self.runner.invoke(app, ["ls", "nonexistent"])
        
        assert result.exit_code == 0  # Should not crash
        assert "Unknown service" in result.stdout
        assert "Supported services:" in result.stdout
        
        # Should suggest valid services
        assert "ec2" in result.stdout
        assert "s3" in result.stdout
    
    def test_cost_command_helpful_menu(self):
        """
        REGRESSION TEST: Cost command without subcommand should show helpful menu
        
        Should not show error, but helpful options
        """
        result = self.runner.invoke(app, ["cost"])
        
        assert result.exit_code == 0
        assert "Which cost analysis would you like?" in result.stdout
        assert "Most Popular:" in result.stdout
        assert "summary" in result.stdout
    
    def test_ls_command_helpful_menu(self):
        """
        REGRESSION TEST: ls command without service should show helpful menu
        
        Should not show error, but helpful service list
        """
        result = self.runner.invoke(app, ["ls"])
        
        assert result.exit_code == 0
        assert "Which AWS service would you like to list?" in result.stdout
        assert "Available services:" in result.stdout
        assert "ec2" in result.stdout


class TestOutputFormatConsistency:
    """Tests to ensure consistent output formatting across commands"""
    
    def setup_method(self):
        self.runner = CliRunner()
    
    def test_all_help_outputs_clean(self):
        """Ensure all command help outputs are clean and consistent"""
        commands_to_test = [
            ["help"],
            ["-h"],
            ["--help"],
            ["ls", "--help"],
            ["cost", "--help"],
            ["audit", "--help"],
            ["version", "--help"],
            ["test", "--help"],
            ["accounts", "--help"]
        ]
        
        for cmd in commands_to_test:
            result = self.runner.invoke(app, cmd)
            
            # All help commands should succeed
            assert result.exit_code == 0, f"Command {' '.join(cmd)} failed"
            
            # None should have markup leakage
            assert "[cyan]" not in result.stdout, f"Markup leakage in {' '.join(cmd)}"
            assert "[bold]" not in result.stdout, f"Markup leakage in {' '.join(cmd)}"
    
    def test_error_messages_are_helpful(self):
        """Ensure error messages provide helpful guidance"""
        # Test various invalid inputs
        invalid_commands = [
            ["ls", "invalid"],
            ["cost", "invalid"],
        ]
        
        for cmd in invalid_commands:
            result = self.runner.invoke(app, cmd)
            
            # Should provide helpful output, not just fail
            assert len(result.stdout) > 50, f"Command {' '.join(cmd)} should provide helpful output"
        
        # Special case for audit with invalid flag - it may exit with code 2 and empty stdout
        # This is acceptable Typer behavior for invalid flags
        result = self.runner.invoke(app, ["audit", "--invalid-flag"])
        assert result.exit_code == 2  # Expected for invalid flags


class TestNetworkSecurityFeatures:
    """Regression tests for network security audit functionality"""
    
    def setup_method(self):
        self.runner = CliRunner()
    
    @patch('aws_super_cli.services.audit.run_security_audit')
    @patch('aws_super_cli.services.audit.get_security_summary')
    def test_network_service_in_default_audit(self, mock_summary, mock_audit):
        """
        REGRESSION TEST: Ensure network service is included in default audit
        
        Network security audit should be part of the default audit services
        """
        mock_audit.return_value = []
        mock_summary.return_value = {
            'score': 100,
            'total': 0,
            'high': 0,
            'medium': 0,
            'low': 0,
            'services': {}
        }
        
        result = self.runner.invoke(app, ["audit", "--summary"])
        assert result.exit_code == 0
        
        # Verify network is in default services
        mock_audit.assert_called_once()
        call_args = mock_audit.call_args
        services = call_args.kwargs['services']
        assert 'network' in services, "Network service should be in default audit services"
    
    @patch('aws_super_cli.services.audit.run_security_audit')
    @patch('aws_super_cli.services.audit.get_security_summary')
    def test_network_only_audit_works(self, mock_summary, mock_audit):
        """
        REGRESSION TEST: Network-only audit should work correctly
        
        Should be able to run audit with only network service
        """
        mock_audit.return_value = []
        mock_summary.return_value = {
            'score': 85,
            'total': 0,
            'high': 0,
            'medium': 0,
            'low': 0,
            'services': {}
        }
        
        result = self.runner.invoke(app, ["audit", "--services", "network", "--summary"])
        assert result.exit_code == 0
        assert "Security Audit Summary" in result.stdout
        
        # Verify only network service was called
        mock_audit.assert_called_once()
        call_args = mock_audit.call_args
        services = call_args.kwargs['services']
        assert services == ['network'], "Should only audit network service when explicitly specified"
    
    def test_help_includes_network_audit_examples(self):
        """
        REGRESSION TEST: Help should include network audit examples
        
        Users should see how to use network security audit
        """
        result = self.runner.invoke(app, ["help"])
        assert result.exit_code == 0
        
        # Should mention network security audit
        assert "--services network" in result.stdout, "Help should show network service option"
        assert "Security Auditing:" in result.stdout, "Help should have security auditing section"
    
    @patch('aws_super_cli.services.audit.run_security_audit')
    @patch('aws_super_cli.services.audit.get_security_summary') 
    def test_audit_services_help_mentions_network(self, mock_summary, mock_audit):
        """
        REGRESSION TEST: Audit command help should mention network service
        
        When users run audit --help, they should see network as an option
        """
        result = self.runner.invoke(app, ["audit", "--help"])
        assert result.exit_code == 0
        
        # Should mention network in services help text
        assert "audit (s3, iam, network," in result.stdout, "Audit help should list network as available service"

    @patch('aws_super_cli.services.audit.run_security_audit')
    @patch('aws_super_cli.services.audit.get_security_summary')
    def test_audit_services_help_mentions_compute(self, mock_summary, mock_audit):
        """
        REGRESSION TEST: Audit command help should mention compute service
        
        When users run audit --help, they should see compute as an option
        """
        result = self.runner.invoke(app, ["audit", "--help"])
        assert result.exit_code == 0
        
        # Should mention compute in services help text
        assert "compute" in result.stdout, "Audit help should list compute as available service"


class TestComputeSecurityFeatures:
    """Regression tests for compute security audit functionality"""
    
    def setup_method(self):
        self.runner = CliRunner()
    
    @patch('aws_super_cli.services.audit.run_security_audit')
    @patch('aws_super_cli.services.audit.get_security_summary')
    def test_compute_service_in_default_audit(self, mock_summary, mock_audit):
        """
        REGRESSION TEST: Ensure compute service is included in default audit
        
        Compute security audit should be part of the default audit services
        """
        mock_audit.return_value = []
        mock_summary.return_value = {
            'score': 100,
            'total': 0,
            'high': 0,
            'medium': 0,
            'low': 0,
            'services': {}
        }
        
        result = self.runner.invoke(app, ["audit", "--summary"])
        assert result.exit_code == 0
        
        # Verify compute is in default services
        mock_audit.assert_called_once()
        call_args = mock_audit.call_args
        services = call_args.kwargs['services']
        assert 'compute' in services, "Compute service should be in default audit services"
    
    @patch('aws_super_cli.services.audit.run_security_audit')
    @patch('aws_super_cli.services.audit.get_security_summary')
    def test_compute_only_audit_works(self, mock_summary, mock_audit):
        """
        REGRESSION TEST: Compute-only audit should work correctly
        
        Should be able to run audit with only compute service
        """
        mock_audit.return_value = []
        mock_summary.return_value = {
            'score': 85,
            'total': 0,
            'high': 0,
            'medium': 0,
            'low': 0,
            'services': {}
        }
        
        result = self.runner.invoke(app, ["audit", "--services", "compute", "--summary"])
        assert result.exit_code == 0
        assert "Security Audit Summary" in result.stdout
        
        # Verify only compute service was called
        mock_audit.assert_called_once()
        call_args = mock_audit.call_args
        services = call_args.kwargs['services']
        assert services == ['compute'], "Should only audit compute service when explicitly specified"
    
    @patch('aws_super_cli.services.audit.run_security_audit')
    @patch('aws_super_cli.services.audit.get_security_summary')
    def test_compute_audit_with_other_services(self, mock_summary, mock_audit):
        """
        REGRESSION TEST: Compute audit should work in combination with other services
        
        Should be able to run audit with compute and other services
        """
        mock_audit.return_value = []
        mock_summary.return_value = {
            'score': 75,
            'total': 0,
            'high': 0,
            'medium': 0,
            'low': 0,
            'services': {}
        }
        
        result = self.runner.invoke(app, ["audit", "--services", "s3,compute", "--summary"])
        assert result.exit_code == 0
        assert "Security Audit Summary" in result.stdout
        
        # Verify both services were called
        mock_audit.assert_called_once()
        call_args = mock_audit.call_args
        services = call_args.kwargs['services']
        assert 's3' in services, "S3 service should be included"
        assert 'compute' in services, "Compute service should be included"
        assert len(services) == 2, "Should only include the two specified services"


class TestGuardDutyIntegrationRegression:
    """Regression tests for GuardDuty integration functionality"""
    
    def setup_method(self):
        self.runner = CliRunner()
    
    @patch('aws_super_cli.services.audit.run_security_audit')
    @patch('aws_super_cli.services.audit.get_security_summary')
    def test_guardduty_service_in_default_audit(self, mock_summary, mock_audit):
        """
        REGRESSION TEST: Ensure GuardDuty service is included in default audit
        
        GuardDuty integration should be part of the default audit services
        """
        mock_audit.return_value = []
        mock_summary.return_value = {
            'score': 100,
            'total': 0,
            'high': 0,
            'medium': 0,
            'low': 0,
            'services': {}
        }
        
        result = self.runner.invoke(app, ["audit", "--summary"])
        assert result.exit_code == 0
        
        # Verify GuardDuty is in default services
        mock_audit.assert_called_once()
        call_args = mock_audit.call_args
        services = call_args.kwargs['services']
        assert 'guardduty' in services, "GuardDuty service should be in default audit services"
    
    @patch('aws_super_cli.services.audit.run_security_audit')
    @patch('aws_super_cli.services.audit.get_security_summary')
    def test_guardduty_only_audit_works(self, mock_summary, mock_audit):
        """
        REGRESSION TEST: GuardDuty-only audit should work correctly
        
        Users should be able to audit only GuardDuty findings
        """
        mock_audit.return_value = []
        mock_summary.return_value = {
            'score': 100,
            'total': 0,
            'high': 0,
            'medium': 0,
            'low': 0,
            'services': {'guardduty': 0}
        }
        
        result = self.runner.invoke(app, ["audit", "--services", "guardduty", "--summary"])
        assert result.exit_code == 0
        
        # Verify only GuardDuty was audited
        mock_audit.assert_called_once()
        call_args = mock_audit.call_args
        services = call_args.kwargs['services']
        assert services == ['guardduty'], "Only GuardDuty should be audited"
    
    @patch('aws_super_cli.services.audit.run_security_audit')
    @patch('aws_super_cli.services.audit.get_security_summary')
    def test_guardduty_audit_with_other_services(self, mock_summary, mock_audit):
        """
        REGRESSION TEST: GuardDuty should work well with other audit services
        
        GuardDuty should integrate seamlessly with s3, iam, network, compute audits
        """
        mock_audit.return_value = []
        mock_summary.return_value = {
            'score': 85,
            'total': 0,
            'high': 0,
            'medium': 0,
            'low': 0,
            'services': {'s3': 0, 'guardduty': 0}
        }
        
        result = self.runner.invoke(app, ["audit", "--services", "s3,guardduty", "--summary"])
        assert result.exit_code == 0
        
        # Verify both services were audited
        mock_audit.assert_called_once()
        call_args = mock_audit.call_args
        services = call_args.kwargs['services']
        assert 's3' in services, "S3 should be audited"
        assert 'guardduty' in services, "GuardDuty should be audited"
    
    def test_help_includes_guardduty_audit_examples(self):
        """
        REGRESSION TEST: Help command should mention GuardDuty audit capability
        
        Users should be able to discover GuardDuty audit functionality through help
        """
        result = self.runner.invoke(app, ["help"])
        assert result.exit_code == 0
        
        # Should mention GuardDuty threat detection
        assert "guardduty" in result.stdout.lower(), "Help should mention GuardDuty"
        assert "threat detection" in result.stdout.lower(), "Help should mention threat detection"
    
    @patch('aws_super_cli.services.audit.run_security_audit')
    @patch('aws_super_cli.services.audit.get_security_summary') 
    def test_audit_services_help_mentions_guardduty(self, mock_summary, mock_audit):
        """
        REGRESSION TEST: Audit command help should list GuardDuty as available service
        
        --services help should include guardduty in the list
        """
        result = self.runner.invoke(app, ["audit", "--help"])
        assert result.exit_code == 0
        
        # Should list GuardDuty as available service
        assert "guardduty" in result.stdout, "Audit help should mention GuardDuty service"
        assert "threats" in result.stdout.lower() or "guardduty" in result.stdout, "Should mention threat detection capability"


if __name__ == "__main__":
    pytest.main([__file__, "-v"]) 