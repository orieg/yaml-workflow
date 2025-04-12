# Simple YAML Workflow Engine

This is a lightweight Python framework for defining and executing workflows using YAML configuration files. It's designed for simple, sequential workflows where you need to run a series of Python functions and pass data between them.

## Features

* **YAML-Driven:** Define your workflow steps and dependencies in a human-readable YAML file.
* **Modular Tasks:** Implement your workflow logic in separate Python modules.
* **Data Passing:** Easily pass data between steps using a runtime context.
* **Basic Error Handling:** Logs errors and exceptions during workflow execution.
* **Runtime Inputs:** Supports passing runtime inputs to the workflow.
* **Basic State management**: In memory state management, and an example of how to make the workflow resumable.

## Getting Started

1.  **Installation:**

    * Clone this repository (if applicable).
    * Install the required dependencies:

        ```bash
        pip install pyyaml
        # Add other dependencies your tasks may require (e.g., jira, requests)
        ```

2.  **Create Your Task Modules:**

    * Create Python modules (e.g., `jira_tasks.py`, `confluence_tasks.py`) that contain the functions you want to execute in your workflow.
    * Ensure your functions accept and return data as needed for your workflow.

3.  **Define Your Workflow in YAML:**

    * Create a YAML file (e.g., `workflow.yaml`) that defines your workflow steps.
    * Use the following structure:

        ```yaml
        workflow:
          steps:
            - name: step_name
              module: module_name
              function: function_name
              inputs:
                input_name: input_value  # Or ${variable_name} for context
              outputs:
                - output_variable_name
        ```

    * `module`: The name of the Python module containing the function.
    * `function`: The name of the function to execute.
    * `inputs`: A dictionary of input arguments for the function. Use `${variable_name}` to reference data from the runtime context.
    * `outputs`: A list of variable names to store the function's output in the context.

4.  **Run the Workflow:**

    * Execute the `run_workflow.py` script, providing the path to your YAML file and any runtime inputs:

        ```bash
        python run_workflow.py workflow.yaml '{"jql_query": "project = MYPROJECT AND status = Done"}'
        ```

    * Make sure to replace the example input with your desired runtime inputs.

## Example

See the provided `workflow.yaml` and the conceptual python code in the previous response for an example workflow that interacts with Jira, Confluence, and Ollama.

## Error Handling and Logging

* The `run_workflow.py` script includes basic error handling using `try-except` blocks.
* The `logging` module is used to log information, warnings, and errors.
* Logs are outputted to the console.

## State Management

* The workflow uses a `context` dictionary to store data between steps.
* For persistent state management, you can modify the script to save the context to a file or database after each step.
* An example of how to make the workflow resumable is given in the previous response.

## Considerations

* **Dependencies:** Manage your dependencies carefully.
* **Security:** Handle API keys and credentials securely.
* **Modularity:** Design your task modules for reusability.
* **Testing:** Write unit tests for your task functions.
* **Scalability**: This is a simple in-process system, consider other solutions for highly scalable workflows.