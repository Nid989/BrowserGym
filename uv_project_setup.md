
# **Setting Up a Project with UV for Local Development: A Detailed Process**

This document outlines the step-by-step process used to set up a project environment using **`uv`**, including managing dependencies, local development modules, and ensuring project reproducibility. 

## **Prerequisites**
Before beginning, ensure you have the following:
- A Python environment management tool (e.g., `pyenv`) to manage your Python versions and environments.
- **`uv`** installed on your system. You can install it using:
  ```bash
  pip install uv
  ```
- A `requirements.txt` file that contains the list of dependencies for your project, generated either from an existing environment or manually.

## **Process Overview**
The process is divided into several key steps:

### **1. Generate `requirements.txt` from an Existing Environment**
To replicate an existing environment or to export dependencies from a `pyenv` virtual environment, follow these steps:

1. **Activate the environment** using `pyenv`:
   ```bash
   pyenv activate <your-env-name>
   ```
   
2. **Generate the `requirements.txt` file** by running:
   ```bash
   pip freeze > requirements.txt
   ```

   This will capture all the installed dependencies into `requirements.txt`. However, local development dependencies, represented by `-e <path-to-local-module>`, may need adjustment if they are sourced from git URLs or paths that don’t align with the desired structure.

### **2. Adjust Local Development Dependencies**
Your `requirements.txt` may contain entries like:
```
-e git+https://github.com/username/repository.git@commit_hash#egg=module_name&subdirectory=path_to_subdirectory
```
**`uv`** does not directly support editable installs using git URLs in `requirements.txt`. 

- **Solution:** Replace the `-e` entries with absolute or relative paths to the local directories where these modules are stored, or ensure the paths point to valid modules that `uv` can recognize.

Example:
```txt
git+https://github.com/username/repository.git@commit_hash#egg=module_name -> path/to/local/module
```

### **3. Create a `uv` Virtual Environment**
Before installing dependencies, set up a virtual environment using `uv`.

Run:
```bash
uv venv <env-name> 
# or
uv venv
```
This will create a virtual environment under the `uv` management, ensuring that all dependencies are installed in an isolated manner.

### **4. Install Dependencies**

At this stage, you have two methods for installing dependencies:

#### **(a) Installing Dependencies with `uv pip`**
You can install all the dependencies listed in the `requirements.txt` file using the following command:
```bash
uv pip install -r requirements.txt
```
This will install the dependencies directly into the virtual environment (`.venv`) created by `uv`. 

- **Pros:** Simple installation without modifying `pyproject.toml` or creating a lock file.
- **Cons:** Does not automatically update `pyproject.toml` or `uv.lock` file, meaning the project’s dependencies may not be tracked correctly for sharing or future installs.

#### **(b) Installing and Adding Dependencies to `pyproject.toml` with `uv add`**
To ensure that your project dependencies are tracked and locked, you can add them to the `pyproject.toml` and update the `uv.lock` file:
```bash
uv add -r requirements.txt
```
This will:
1. Install the dependencies from `requirements.txt`.
2. Automatically add the dependencies to the `pyproject.toml` file.
3. Update the `uv.lock` file, ensuring a reproducible environment for sharing with others.

- **Pros:** The `pyproject.toml` and `uv.lock` files will be updated, providing a consistent environment across all devices.
- **Cons:** Requires `uv` for tracking and dependency management (which replaces direct `pip` commands in this case).

### **5. Locking Dependencies for Reproducibility**

Once the dependencies are added to `pyproject.toml` and installed, it is important to generate a lock file that captures the exact versions of the installed dependencies to ensure reproducibility across different devices and environments.

Run:
```bash
uv lock
```
This will generate the `uv.lock` file, which locks down the installed versions of dependencies as they are installed in your environment.

**Important:** The `uv.lock` file should be shared along with the `pyproject.toml` to ensure other developers or devices can install the exact same environment.

### **6. Installing on a New Device or Environment**

To install the dependencies in a new environment on another device:

1. **Transfer** the `pyproject.toml` and `uv.lock` files to the new system.
2. **Create a new virtual environment**:
   ```bash
   uv venv <new-env-name>
   ```
3. **Install dependencies** using:
   ```bash
   uv install
   ```

This will read the `pyproject.toml` and `uv.lock` files and install the exact versions of the dependencies on the new system, ensuring a consistent environment.

### **7. Managing Local Development Modules**

For local development modules that need to be added directly from git or local paths, ensure that the paths in the `requirements.txt` are adjusted before running the installation steps. Since `uv` does not natively support `-e` (editable installations) with git URLs, you must either:
- Replace `-e` URLs with relative or absolute paths to the modules.
- Add them directly to `pyproject.toml` using `uv add`.

---

## **Summary of Commands:**
Here is a quick overview of the relevant commands you need to use:

1. **Create Virtual Environment:**
   ```bash
   uv venv <env-name>
   ```

2. **Install Dependencies via `requirements.txt`:**
   - Install dependencies only:
     ```bash
     uv pip install -r requirements.txt
     ```
   - Install dependencies and update `pyproject.toml` and `uv.lock`:
     ```bash
     uv add -r requirements.txt
     ```

3. **Lock Dependencies for Reproducibility:**
   ```bash
   uv lock
   ```

4. **Install Dependencies on a New Device:**
   - Install from `pyproject.toml` and `uv.lock`:
     ```bash
     uv install
     ```

---

## **Conclusion**

By following this process, you ensure that your project dependencies are properly managed and tracked using `uv`. The key benefits of using `uv` with `pyproject.toml` and `uv.lock` include:
- **Reproducibility**: Ensuring that every developer or device uses the same versions of dependencies.
- **Simplicity**: Using `uv` to manage environments and dependencies simplifies the workflow, reducing the need for complex manual steps.
- **Scalability**: With a proper setup, it becomes easier to scale your project across different systems without worrying about environment inconsistencies.