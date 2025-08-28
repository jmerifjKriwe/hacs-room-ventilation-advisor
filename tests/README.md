# Solar Window System - Test Documentation

## Overview

This document provides comprehensive guidance for testing the Solar Window System integration for Home Assistant. The test suite ensures reliability, performance, and compatibility with Home Assistant's architecture.

### Test Suite Architecture

The test suite is organized into several categories:

```
tests/
├── __init__.py
├── conftest.py                    # Shared fixtures and configuration
├── test_data.py                   # Centralized test data
├── config_flow/                   # Configuration flow tests
│   ├── test_config_flow.py
│   ├── test_group_flow.py
│   └── test_window_flow.py
├── integration/                   # End-to-end integration tests
│   └── test_solar_calculation_workflows.py
├── platforms/                     # Platform-specific entity tests
│   ├── test_binary_sensor_platform.py
│   ├── test_calculator_platform.py
│   ├── test_number_platform.py
│   ├── test_select_platform.py
│   ├── test_sensor_platform.py
│   ├── test_switch_platform.py
│   └── test_text_platform.py
├── helpers/                       # Helper function tests
├── services/                      # Service handler tests
└── README.md                      # This documentation
```

### Test Types

- **Unit Tests**: Test individual functions and classes in isolation
- **Integration Tests**: Test component interactions and end-to-end workflows
- **Platform Tests**: Test entity platforms (sensors, switches, etc.)
- **Config Flow Tests**: Test configuration and setup workflows
- **Snapshot Tests**: Validate complex outputs using syrupy

## Running Tests

### Prerequisites

Ensure you have the test dependencies installed:

```bash
pip install -r requirements_test.txt
```

### Basic Test Execution

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/platforms/test_sensor_platform.py

# Run specific test
pytest tests/platforms/test_sensor_platform.py::test_sensor_entity_creation

# Run with verbose output
pytest -v

# Stop on first failure
pytest -x

# Run only failed tests
pytest --lf
```

### Coverage Analysis

```bash
# Generate coverage report
pytest --cov=custom_components.solar_window_system --cov-report=term

# Generate HTML coverage report
pytest --cov=custom_components.solar_window_system --cov-report=html

# Show missing lines for specific module
pytest --cov=custom_components.solar_window_system.calculator --cov-report=term-missing
```

### Test Filtering

```bash
# Run tests by name pattern
pytest -k "config_flow"

# Run tests by marker
pytest -m "asyncio"

# Run tests in specific directory
pytest tests/config_flow/

# Run tests excluding certain patterns
pytest -k "not slow"
```

## Test Architecture & Best Practices

### Core Testing Principles

1. **Isolation**: Each test should be independent and not rely on other tests
2. **Clarity**: Tests should be easy to understand and maintain
3. **Coverage**: Aim for comprehensive coverage of all code paths
4. **Performance**: Tests should run efficiently
5. **Reliability**: Tests should be deterministic and not flaky

### Home Assistant Integration Testing

#### MockConfigEntry Setup

```python
from homeassistant import config_entries
from pytest_homeassistant_custom_component.common import MockConfigEntry

@pytest.fixture
def mock_config_entry():
    """Create a mock config entry for testing."""
    return MockConfigEntry(
        domain=DOMAIN,
        data={
            "name": "Test Window",
            "latitude": 52.0,
            "longitude": 13.0,
            # ... other config data
        },
        entry_id="test_entry_id",
        version=1,
    )
```

#### Async Test Patterns

```python
@pytest.mark.asyncio
async def test_async_function(hass, mock_config_entry):
    """Test async function with proper setup."""
    mock_config_entry.add_to_hass(hass)

    # Test async operations
    result = await async_function_call()
    assert result is not None
```

#### Entity Testing

```python
async def test_entity_creation(hass, mock_config_entry):
    """Test that entities are created correctly."""
    mock_config_entry.add_to_hass(hass)

    # Setup integration
    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    # Verify entity exists
    entity_id = "sensor.test_window_solar_irradiance"
    state = hass.states.get(entity_id)
    assert state is not None
    assert state.state != "unknown"
```

### Common Testing Patterns

#### Patching External Dependencies

```python
from unittest.mock import patch, AsyncMock

@pytest.mark.asyncio
async def test_with_mocked_api(hass, mock_config_entry):
    """Test with mocked external API calls."""
    with patch("custom_components.solar_window_system.api.get_solar_data") as mock_api:
        mock_api.return_value = AsyncMock(return_value={"irradiance": 800})

        mock_config_entry.add_to_hass(hass)
        await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()

        # Verify API was called
        mock_api.assert_called_once()
```

#### Testing State Changes

```python
async def test_state_updates(hass, mock_config_entry):
    """Test that entity states update correctly."""
    mock_config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    # Get initial state
    entity_id = "sensor.test_window_solar_irradiance"
    initial_state = hass.states.get(entity_id)

    # Trigger update (e.g., via service call or time change)
    await trigger_update()

    # Verify state changed
    updated_state = hass.states.get(entity_id)
    assert updated_state.state != initial_state.state
```

## Config Flow Testing

### Main Configuration Flow

```python
@pytest.mark.asyncio
async def test_config_flow_success(hass):
    """Test successful config flow."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    # Complete flow steps
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            "name": "Test Window",
            "latitude": 52.0,
            "longitude": 13.0,
        }
    )

    assert result["type"] == "create_entry"
    assert result["data"]["name"] == "Test Window"
```

### Subentry Flow Testing

#### Group Subentry Flow

```python
@pytest.mark.asyncio
async def test_group_subentry_flow(hass, mock_config_entry):
    """Test group subentry flow configuration."""
    mock_config_entry.add_to_hass(hass)

    # Initialize subentry flow
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={
            "source": "group",
            "group_id": mock_config_entry.entry_id
        }
    )

    # Configure group settings
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            "group_name": "Living Room Windows",
            "window_count": 3,
        }
    )

    assert result["type"] == "create_entry"
```

#### Window Subentry Flow

```python
@pytest.mark.asyncio
async def test_window_subentry_flow(hass, mock_config_entry):
    """Test window subentry flow configuration."""
    mock_config_entry.add_to_hass(hass)

    # Initialize window subentry flow
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={
            "source": "window",
            "window_id": "window_1"
        }
    )

    # Configure window-specific settings
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            "window_name": "South Window",
            "orientation": "south",
            "tilt_angle": 30,
        }
    )

    assert result["type"] == "create_entry"
```

### Important Testing Rules (2025-08)

#### Current Architecture Requirements

- **Main Config Flow**: Only for initial integration setup. Will abort with 'already_configured' for subsequent runs.
- **Subentry Flows**: Required for group and window configuration. Use `GroupSubentryFlowHandler` and `WindowSubentryFlowHandler`.
- **Options Flow**: Not supported for window or group configuration. Will abort with `reason: not_supported`.
- **Legacy Patterns**: All tests using options flow for group/window config must be refactored to use subentry flows.

#### Subentry Flow Testing Guidelines

- **Direct Handler Instantiation**: Create subentry flow handlers directly instead of using options flow
- **Proper Context**: Use correct context parameters (`group_id`, `window_id`) for subentry initialization
- **Data Patching**: Mock subentry/group/global data as needed for isolated testing
- **Flow Steps**: Drive flows through their proper steps (`async_step_user`, `async_step_enhanced`, etc.)
- **No Options Flow**: Do not use OptionsFlow for window or group config/inheritance logic

#### Deprecated Patterns (Do Not Use)

- The legacy pattern of testing group/config inheritance via the options flow is no longer supported and will abort with `reason: not_supported`.
- To test group/window inheritance, instantiate the appropriate subentry flow handler and drive it through its steps (`async_step_user`, `async_step_enhanced`, etc.), patching subentry/group/global data as needed.
- Do not use OptionsFlow for window or group config/inheritance logic; this is reserved for other entity types if implemented.
- See `test_group_flow.py`, `test_group_flow_fixed.py`, and `test_group_flow_defaults.py` for correct, modern test patterns.

#### Deprecated: Window Options Flow Testing

- As of August 2025, **window options flow is not supported**. Any attempt to test window configuration via the options flow will abort with `reason: not_supported`.
- The test `test_window_second_save_bug.py` was removed because it attempted to test window options flow, which is now architecturally unsupported. All window configuration/inheritance logic must be tested via the `WindowSubentryFlowHandler`.
- If you need to test window config/inheritance, use the subentry flow handler directly as described above.

#### Refactoring Note (2025-08)

- All legacy group flow tests using the options flow have been refactored to use the subentry flow handler directly. This is now the only supported and future-proof approach. If you see a test using the options flow for group/window config, it is outdated and must be refactored.

### Test Refactoring Workflow

- **Test Refactoring Workflow:**
  - Always refactor one test file at a time: refactor, ensure all tests are green, then proceed to the next file.
  - Reactivate and green all previously skipped tests as part of the refactor.
  - Convert all class-based or skipped tests to function-based, following pytest and Home Assistant best practices.
  - Use clear, descriptive docstrings and ensure all test logic matches the actual config flow/subentry flow implementation.

### Troubleshooting

- **Troubleshooting:**
  - If a test fails due to `UnknownFlow` or similar, verify that the correct flow handler is used and that the test setup matches the integration's actual config flow logic.
  - If main config flow aborts with 'already_configured', this is expected - use SubentryFlows for group/window testing
  - Always check Home Assistant documentation for current SubentryFlow testing patterns

_These rules are based on recent refactoring and bugfixes (2025-08) and should be followed for all future test maintenance._
