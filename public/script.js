class SimpleIDE {
    constructor() {
        this.editor = null;

        this.elements = {
            runBtn: document.getElementById('run-btn'),
            clearBtn: document.getElementById('clear-btn'),
            languageSelector: document.getElementById('language-selector'),
            output: document.getElementById('output'),
            // ADDED: The new input textarea element
            inputData: document.getElementById('input-data') 
        };

        this.placeholders = {
            // Updated example to demonstrate input
            python: 'name = input("Enter your name: ")\nprint(f"Hello, {name}!")',
            javascript: '// To read from stdin in Node.js:\n// process.stdin.on("data", data => console.log(`You entered: ${data}`));\nconsole.log("Hello, world!");'
        };

        this.initializeEditor();
        this.bindEvents();
    }

    initializeEditor() {
        require.config({ paths: { 'vs': 'https://cdn.jsdelivr.net/npm/monaco-editor@0.34.1/min/vs' }});
        require(['vs/editor/editor.main'], () => {
            this.editor = monaco.editor.create(document.getElementById('editor'), {
                value: this.placeholders.python,
                language: 'python',
                theme: 'vs-dark',
                automaticLayout: true,
                fontSize: 14,
                minimap: { enabled: false }
            });

            this.editor.addCommand(monaco.KeyMod.CtrlCmd | monaco.KeyCode.Enter, () => {
                this.runCode();
            });
        });
    }

    bindEvents() {
        this.elements.runBtn.addEventListener('click', () => this.runCode());
        this.elements.clearBtn.addEventListener('click', () => this.clearAll());
        this.elements.languageSelector.addEventListener('change', () => this.handleLanguageChange());
    }

    handleLanguageChange() {
        const selectedLanguage = this.elements.languageSelector.value;
        monaco.editor.setModelLanguage(this.editor.getModel(), selectedLanguage);
        this.editor.setValue(this.placeholders[selectedLanguage] || '');
    }

    async runCode() {
        if (!this.editor) return;

        const code = this.editor.getValue();
        const language = this.elements.languageSelector.value;
        // ADDED: Get the value from the input textarea
        const inputData = this.elements.inputData.value;
        
        this.elements.output.textContent = 'Executing...';
        this.elements.output.classList.remove('error');

        try {
            const response = await fetch('/api/execute', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                // UPDATED: Include the input_data in the JSON payload
                body: JSON.stringify({ language, code, input_data: inputData })
            });
            const result = await response.json();

            this.elements.output.textContent = result.output;
            if (result.error) {
                this.elements.output.classList.add('error');
            }
        } catch (error) {
            this.elements.output.textContent = `Error: ${error.message}`;
            this.elements.output.classList.add('error');
        }
    }

    clearAll() {
        this.elements.output.textContent = '';
        this.elements.output.classList.remove('error');
        this.editor.setValue('');
        // ADDED: Clear the input box as well
        this.elements.inputData.value = '';
    }
}

document.addEventListener('DOMContentLoaded', () => {
    new SimpleIDE();
});
