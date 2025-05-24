#!/bin/bash
echo "Activating conda environment at e:/Github Repositories/codelens/.conda"
conda activate "e:/Github Repositories/codelens/.conda"

if [ $? -eq 0 ]; then
    echo "Conda environment activated successfully."
    echo "You can now run your Flask application."
else
    echo "Failed to activate conda environment."
    echo "If using a named environment, try:"
    echo "conda env list"
    echo "conda activate environment_name"
    echo "Or if path-based activation is not working, consider creating a symlink or named environment."
fi
