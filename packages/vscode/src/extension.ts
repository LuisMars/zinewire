import * as vscode from "vscode";
import { PreviewPanel } from "./preview-panel";

export function activate(context: vscode.ExtensionContext) {
  context.subscriptions.push(
    vscode.commands.registerCommand(
      "zinewire.openPreview",
      (uri?: vscode.Uri) => {
        // Determine the project root from whichever file triggered the command
        const targetUri =
          uri ||
          vscode.window.activeTextEditor?.document.uri;

        if (!targetUri) {
          vscode.window.showInformationMessage(
            "zinewire: Open a zinewire.toml or markdown file first."
          );
          return;
        }

        PreviewPanel.createOrShow(context, targetUri);
      }
    )
  );

  // Rebuild on save of any .md or zinewire.toml in the project
  context.subscriptions.push(
    vscode.workspace.onDidSaveTextDocument((doc) => {
      if (
        doc.languageId === "markdown" ||
        doc.fileName.endsWith(".toml") ||
        doc.languageId === "css" ||
        doc.fileName.endsWith(".css")
      ) {
        PreviewPanel.rebuild();
      }
    })
  );
}

export function deactivate() {
  PreviewPanel.dispose();
}
