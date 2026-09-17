---
name: ros2-launch-management
description: Create, configure, and debug ROS 2 launch files using Python launch API. Use when asked to create launch files, configure launch parameters, debug launch issues, compose launch files, handle launch events, coordinate multi-robot launches, or troubleshoot node startup problems. Supports parameter passing, substitutions, event handlers, and launch file includes.

---

# ROS 2 Launch Management

Create and manage ROS 2 launch files for orchestrating multi-node systems with parameter configuration, event handling, and composition.

## When to Use This Skill

- Create new launch files for single or multiple nodes
- Configure launch parameters and pass them to nodes
- Debug launch file issues and node startup problems
- Compose launch files using includes
- Handle launch events (process started, exited, etc.)
- Set up multi-robot or multi-machine launches
- Use launch substitutions and conditionals
- Troubleshoot "launch file not found" or parameter errors

## Prerequisites

- ROS 2 Jazzy installation
- Workspace with packages containing launch directories
- Python 3.8+ (launch files use Python API)
- Understanding of ROS 2 node parameters
- `ros2 launch` command available

## Launch File Structure

| Component | Purpose | Example |
|-----------|---------|---------|
| **Import statements** | Load launch API modules | `from launch import LaunchDescription` |
| **Node declarations** | Define nodes to launch | `Node(package='pkg', executable='node')` |
| **Parameters** | Pass configuration to nodes | `parameters=[{'param': value}]` |
| **Substitutions** | Dynamic value resolution | `PathJoinSubstitution`, `LaunchConfiguration` |
| **Event handlers** | React to process events | `RegisterEventHandler` |
| **Includes** | Compose from other launch files | `IncludeLaunchDescription` |

## Step-by-Step Workflows

### Workflow 1: Create Basic Launch File for Single Node

Create a simple launch file to start one node with parameters.

1. Navigate to package launch directory:
   ```bash
   cd <workspace_root>/packages/runtime/<package_name>/launch/
   ```

2. Create launch file (e.g., `basic.launch.py`):
   ```python
   from launch import LaunchDescription
   from launch_ros.actions import Node

   def generate_launch_description():
       return LaunchDescription([
           Node(
               package='<package_name>',
               executable='<node_executable>',
               name='<node_name>',
               output='screen',
               parameters=[{
                   'param1': 'value1',
                   'param2': 42,
                   'param3': True
               }]
           )
       ])
   ```

3. Test the launch file:
   ```bash
   source scripts/setup.bash
   ros2 launch <package_name> basic.launch.py
   ```

4. Verify node started correctly with `ros2 node list`

**When to use**: Simple single-node launches with static configuration

### Workflow 2: Create Launch File with Multiple Nodes and Namespaces

Launch multiple nodes with different configurations and namespaces.

1. Create launch file with multiple nodes:
   ```python
   from launch import LaunchDescription
   from launch_ros.actions import Node

   def generate_launch_description():
       # Node 1: Serial driver
       serial_node = Node(
           package='drqp_serial',
           executable='serial_node',
           name='serial_driver',
           namespace='robot1',
           output='screen',
           parameters=[{
               'port': '/dev/ttyUSB0',
               'baudrate': 115200
           }]
       )

       # Node 2: Controller
       controller_node = Node(
           package='drqp_control',
           executable='controller_node',
           name='controller',
           namespace='robot1',
           output='screen',
           parameters=[{
               'update_rate': 50.0,
               'control_mode': 'position'
           }]
       )

       return LaunchDescription([
           serial_node,
           controller_node
       ])
   ```

2. Launch the system:
   ```bash
   ros2 launch <package_name> multi_node.launch.py
   ```

3. Verify nodes are in correct namespace:
   ```bash
   ros2 node list
   # Expected: /robot1/serial_driver, /robot1/controller
   ```

**When to use**: Multi-node systems requiring coordination and namespacing

### Workflow 3: Launch File with Parameters from YAML File

Load parameters from external YAML configuration files.

1. Create parameters YAML file (`config/robot_params.yaml`):
   ```yaml
   /**:
     ros__parameters:
       robot_name: "Dr.QP"
       max_velocity: 1.5
       control_frequency: 50
   ```

2. Create launch file that loads YAML:
   ```python
   import os
   from launch import LaunchDescription
   from launch_ros.actions import Node
   from ament_index_python.packages import get_package_share_directory

   def generate_launch_description():
       # Get package directory
       pkg_dir = get_package_share_directory('<package_name>')
       params_file = os.path.join(pkg_dir, 'config', 'robot_params.yaml')

       node = Node(
           package='<package_name>',
           executable='<node_executable>',
           name='<node_name>',
           output='screen',
           parameters=[params_file]
       )

       return LaunchDescription([node])
   ```

3. Ensure YAML is installed by adding to `CMakeLists.txt`:
   ```cmake
   install(DIRECTORY config
     DESTINATION share/${PROJECT_NAME}
   )
   ```

4. Rebuild and launch:
   ```bash
   colcon build --packages-select <package_name>
   source scripts/setup.bash
   ros2 launch <package_name> params.launch.py
   ```

5. Verify parameters loaded:
   ```bash
   ros2 param list /<node_name>
   ```

**When to use**: Complex parameter configurations, multiple environments (dev/prod)

### Workflow 4: Launch File with Conditionals and Substitutions

Use launch arguments and conditionals for flexible configuration.

1. Create launch file with arguments:
   ```python
   from launch import LaunchDescription
   from launch.actions import DeclareLaunchArgument
   from launch.conditions import IfCondition
   from launch.substitutions import LaunchConfiguration
   from launch_ros.actions import Node

   def generate_launch_description():
       # Declare arguments
       use_sim_arg = DeclareLaunchArgument(
           'use_sim',
           default_value='false',
           description='Use simulation instead of real hardware'
       )

       robot_name_arg = DeclareLaunchArgument(
           'robot_name',
           default_value='robot1',
           description='Name of the robot'
       )

       # Use arguments in node configuration
       hardware_node = Node(
           package='drqp_serial',
           executable='serial_node',
           name='serial_driver',
           condition= UnlessCondition(
               LaunchConfiguration('use_sim', default='false')
           ),
           parameters=[{
               'robot_name': LaunchConfiguration('robot_name')
           }]
       )

       return LaunchDescription([
           use_sim_arg,
           robot_name_arg,
           hardware_node
       ])
   ```

2. Launch with arguments:
   ```bash
   ros2 launch <package_name> conditional.launch.py use_sim:=true robot_name:=drqp1
   ```

3. View available arguments:
   ```bash
   ros2 launch <package_name> conditional.launch.py --show-args
   ```

**When to use**: Flexible launches for different environments, testing vs production

### Workflow 5: Compose Launch Files with Includes

Build complex launch configurations by including other launch files.

1. Create base launch file (`base.launch.py`):
   ```python
   from launch import LaunchDescription
   from launch_ros.actions import Node

   def generate_launch_description():
       return LaunchDescription([
           Node(
               package='drqp_serial',
               executable='serial_node',
               name='serial_driver'
           )
       ])
   ```

2. Create main launch file that includes base:
   ```python
   import os
   from launch import LaunchDescription
   from launch.actions import IncludeLaunchDescription
   from launch.launch_description_sources import PythonLaunchDescriptionSource
   from launch_ros.actions import Node
   from ament_index_python.packages import get_package_share_directory

   def generate_launch_description():
       pkg_dir = get_package_share_directory('<package_name>')

       # Include base launch file
       base_launch = IncludeLaunchDescription(
           PythonLaunchDescriptionSource(
               os.path.join(pkg_dir, 'launch', 'base.launch.py')
           )
       )

       # Add additional nodes
       controller_node = Node(
           package='drqp_control',
           executable='controller_node',
           name='controller'
       )

       return LaunchDescription([
           base_launch,
           controller_node
       ])
   ```

3. Launch the composed system:
   ```bash
   ros2 launch <package_name> main.launch.py
   ```

**When to use**: Modular launch configurations, reusable component launches

### Workflow 6: Debug Launch File Issues

Troubleshoot launch file problems and node startup failures.

1. Enable verbose output:
   ```bash
   ros2 launch <package_name> <launch_file> --debug
   ```

2. Check launch file syntax without running:
   ```bash
   python3 <launch_file_path>
   # Should complete without errors if syntax is valid
   ```

3. View launch file tree structure:
   ```bash
   ros2 launch <package_name> <launch_file> --show-all-subprocesses-output
   ```

4. Check if package and executables exist:
   ```bash
   ros2 pkg prefix <package_name>
   ls $(ros2 pkg prefix <package_name>)/lib/<package_name>/
   ```

5. Test node separately without launch:
   ```bash
   ros2 run <package_name> <executable>
   ```

6. Check parameter file syntax:
   ```bash
   cat <params_file>.yaml
   # Verify YAML syntax is correct
   ```

7. Monitor node output during launch:
   ```bash
   ros2 launch <package_name> <launch_file> 2>&1 | tee launch.log
   ```

**When to use**: Launch file errors, nodes failing to start, parameter issues

## Common Launch Patterns

| Pattern | Use Case | Key Components |
|---------|----------|----------------|
| **Single Node** | Simple node startup | `Node()` with parameters |
| **Multi-Node** | Coordinated system | Multiple `Node()` declarations |
| **Parameterized** | External configuration | YAML files, `parameters=` |
| **Conditional** | Environment-specific | `DeclareLaunchArgument`, `IfCondition` |
| **Composed** | Modular systems | `IncludeLaunchDescription` |
| **Event-Driven** | Process monitoring | `RegisterEventHandler` |

## Troubleshooting

| Issue | Cause | Solution |
|-------|-------|----------|
| "Package not found" | Package not installed or not sourced | Rebuild package and `source scripts/setup.bash` |
| "Executable not found" | Wrong executable name or not built | Check `install/<pkg>/lib/<pkg>/` for executables |
| "Launch file not found" | Wrong path or not installed | Verify launch file in `install/<pkg>/share/<pkg>/launch/` |
| Parameters not loaded | Wrong YAML syntax or file path | Validate YAML syntax, check file exists in install |
| Node crashes immediately | Parameter mismatch or missing dependencies | Check node logs, verify required parameters |
| Multiple nodes same name | Name collision | Use unique names or namespaces |
| Include not working | Wrong package name or launch file path | Verify `get_package_share_directory()` returns correct path |
| Arguments not passed | Wrong syntax in command line | Use `arg_name:=value` (colon-equals) not equals |

## Launch File Installation

To make launch files available after building:

1. Add to `CMakeLists.txt`:
   ```cmake
   # Install launch files
   install(DIRECTORY launch
     DESTINATION share/${PROJECT_NAME}
   )
   ```

2. Rebuild package:
   ```bash
   colcon build --packages-select <package_name>
   ```

3. Launch files available in `install/<package>/share/<package>/launch/`

## References

- [ROS 2 Launch Documentation](https://docs.ros.org/en/jazzy/Tutorials/Intermediate/Launch/Launch-Main.html)
- [Launch File Examples](https://docs.ros.org/en/jazzy/How-To-Guides/Launch-file-different-formats.html)
- [Launch Python API](https://docs.ros.org/en/jazzy/p/launch/)
