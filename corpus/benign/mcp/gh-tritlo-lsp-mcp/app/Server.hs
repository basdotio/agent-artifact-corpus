{-# LANGUAGE OverloadedStrings #-}
{-# LANGUAGE RecordWildCards #-}
{-# LANGUAGE ScopedTypeVariables #-}

module Main where

import Control.Exception (SomeException, try)
import Control.Monad (void, when)
import Control.Monad.IO.Class (liftIO)
import Control.Monad.State (StateT, evalStateT, lift)
import Data.Maybe (mapMaybe)
import Data.Text qualified as T
import Data.Text.IO as TIO
import Data.Text.Utf16.Rope qualified as Rope
import Language.LSP.Protocol.Message qualified as LSP
import Language.LSP.Protocol.Types qualified as LSP
import Language.LSP.Server (Handlers, LspM, Options (..), ServerDefinition (..))
import Language.LSP.Server qualified as LSP
import Language.LSP.VFS qualified as LSP
import Options.Applicative
import System.Directory (getTemporaryDirectory, removeFile)
import System.Exit (exitSuccess)
import System.FilePath ((</>))
import System.Log.Logger qualified as Logger
import Data.Char qualified as Char

newtype LSPOpts = LSPOpts {opt_version :: Bool}

-- | Parse the command line options. This is just to print the version and exit,
-- as some editors query the binary for this information (nvim)
parseLSPOpts :: Parser LSPOpts
parseLSPOpts =
  LSPOpts
    <$> switch
      ( long "version"
          <> short 'v'
          <> help "Print the version and exit"
      )

-- | The program version
lspVersion :: T.Text
lspVersion = "0.1.0.0"

-- | The lsp-mcp Language Server Protocol (LSP) server as a demo
main :: IO ()
main = do
  -- Parse command line options
  opts <-
    execParser $
      info
        (parseLSPOpts <**> helper)
        ( fullDesc
            <> progDesc "simple Language Server Protocol (LSP) server"
            <> header "mcp-lsp - LSP server for simple language"
        )

  -- Check if we should print the version and exit
  when (opt_version opts) $ do
    TIO.putStrLn ("mcp-lsp " <> lspVersion)
    exitSuccess

  -- Set up logging. These can be viewed in your editor's LSP log.
  Logger.updateGlobalLogger "mcp-lsp" (Logger.setLevel Logger.INFO)

  -- Run the server
  void $
    LSP.runServer $
      -- We keep the server definition as short as possible.
      ServerDefinition
        { onConfigChange = const $ pure ()
        , defaultConfig = ()
        , doInitialize = const . pure . Right
        , -- Here we pass the handlers which implement the actual functionality
          staticHandlers = const handlers
        , -- When we run the handlers, we need to include the VFS state, which is our
          -- in-memory representation of the files. It starts empty, and is updated
          -- by the notification handlers.
          interpretHandler = \env -> LSP.Iso (LSP.runLspT env . flip evalStateT LSP.emptyVFS) liftIO
        , -- We need to set these to ensure that we update the VFS with the latest changes
          options =
            LSP.defaultOptions
              { optTextDocumentSync =
                  Just $
                    LSP.TextDocumentSyncOptions
                      (Just True) -- receive open and close notifications
                      (Just LSP.TextDocumentSyncKind_Incremental) -- receive change notifications
                      (Just False) -- receive will save notifications
                      (Just False) -- receive will save wait until notifications
                      (Just $ LSP.InL False) -- do not include the document in the save notification
              }
        , parseConfig = const $ pure $ Right ()
        , configSection = "simple"
        }

-- | A simple completion item with no additional information
simpleCompletion :: LSP.Position -> T.Text -> T.Text -> LSP.CompletionItem
simpleCompletion pos label t =
  LSP.CompletionItem
    label -- The text displayed in the completion list
    Nothing
    (Just LSP.CompletionItemKind_Keyword)
    -- \^ The kind of completion item, which can be used by the editor to display different icons
    Nothing
    Nothing
    Nothing
    Nothing
    Nothing
    Nothing
    Nothing
    Nothing
    Nothing
    Nothing
    (Just $ LSP.InL $ LSP.TextEdit (LSP.Range pos pos) t)
    -- \^ our edit. This range means "put it at the end"
    Nothing
    Nothing
    Nothing
    Nothing
    Nothing

newtype LSPState = StateT LSP.VFS

-- | The handlers for the simple LSP server
handlers :: Handlers (StateT LSP.VFS (LspM ()))
handlers =
  mconcat
    -- Run when the server starts
    [ LSP.notificationHandler LSP.SMethod_Initialized $ const $ do
        liftIO $ Logger.infoM "mcp-lsp" "Server initialized!"
    , -- These are required to keep the VFS synced, allowing us to do completions even if
      -- the file has not been saved.
      LSP.notificationHandler LSP.SMethod_TextDocumentDidOpen (LSP.openVFS mempty)
    , LSP.notificationHandler LSP.SMethod_TextDocumentDidChange (LSP.changeFromClientVFS mempty)
    , LSP.notificationHandler LSP.SMethod_TextDocumentDidClose (LSP.closeVFS mempty)
    , -- Run when the configuration changes. We don't do any configuration yet, but we could.
      LSP.notificationHandler LSP.SMethod_WorkspaceDidChangeConfiguration $ \_ -> do
        liftIO $ Logger.infoM "mcp-lsp" "Configuration changed!"
    , -- TODO: we should probably update the VFS here, i.e. if the files change on disk
      LSP.notificationHandler LSP.SMethod_WorkspaceDidChangeWatchedFiles $ \_ -> do
        liftIO $ Logger.infoM "mcp-lsp" "Watched files changed!"
    , -- The hover functionality
      LSP.requestHandler LSP.SMethod_TextDocumentHover $ \req responder -> do
        let no_resp = responder $ Right $ LSP.InR LSP.Null -- no hover information
        let markup_resp t mb_range =
              -- The response. We just return plain text for now
              -- \^ ^
              -- \| |- The range to highlight in the document
              -- \|- The text to display
              responder $
                Right $
                  LSP.InL $
                    LSP.Hover (LSP.InL $ LSP.MarkupContent LSP.MarkupKind_PlainText t) mb_range
        case req of
          LSP.TRequestMessage _ _ _ (LSP.HoverParams (LSP.TextDocumentIdentifier uri) pos@(LSP.Position ln _) _) -> do
            doc <- lift $ LSP.getVirtualFile $ LSP.toNormalizedUri uri
            case doc of
              Nothing -> no_resp
              -- We lookup the file in the VFS and extract the current line and word if possible
              Just vfs | Just pos_word <- getCurWord vfs pos -> do
                let hover_text = "This is a hover text for " <> pos_word
                markup_resp hover_text (Just $ LSP.Range pos pos)
    , LSP.requestHandler LSP.SMethod_TextDocumentCompletion $ \req responder -> do
        case req of
          LSP.TRequestMessage _ _ _ (LSP.CompletionParams (LSP.TextDocumentIdentifier uri) pos _ _ _) -> do
            doc <- lift $ LSP.getVirtualFile $ LSP.toNormalizedUri uri
            case doc of
              Nothing -> responder $ Right $ LSP.InL []
              Just vfs | Just pos_word <- getCurWord vfs pos -> do
                let toFullSugg c = simpleCompletion pos tc <$> T.stripPrefix pos_word tc
                      where
                        tc = T.pack c
                completions <- return [T.unpack $ pos_word] -- Here we would generate completionss
                responder $ Right $ LSP.InL $ mapMaybe toFullSugg completions
              Just _ -> do
                liftIO $ Logger.errorM "mcp-lsp" "Invalid position"
                responder $ Right $ LSP.InL []
    ]

    where
      getCurWord :: LSP.VirtualFile -> LSP.Position -> Maybe T.Text
      getCurWord (LSP.VirtualFile _ _ rope) (LSP.Position l c) = do
          let rp_pos :: Rope.Position
              rp_pos = Rope.Position (fromIntegral l) (fromIntegral c)
          (before, after) <- Rope.splitAtPosition rp_pos rope
          let aw = T.takeWhile (not . Char.isSpace) $ Rope.toText after
          let bw = T.takeWhileEnd (not . Char.isSpace) $ Rope.toText before
          return $ aw <> bw
