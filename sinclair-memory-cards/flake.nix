{
  description = "Sinclair BASIC memory-card PDF generator (Python)";

  inputs.nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";

  outputs = { self, nixpkgs }:
    let
      systems = [ "x86_64-linux" "aarch64-linux" "x86_64-darwin" "aarch64-darwin" ];
      forAllSystems = f:
        nixpkgs.lib.genAttrs systems (system: f nixpkgs.legacyPackages.${system});

      # Python with exactly the runtime dependencies the generator needs.
      pythonEnvFor = pkgs: pkgs.python3.withPackages (ps: with ps; [
        reportlab
        anthropic
        openai
      ]);
    in
    {
      devShells = forAllSystems (pkgs: {
        default = pkgs.mkShell {
          packages = [ (pythonEnvFor pkgs) ];
          shellHook = ''
            echo "sinclair-memory-cards dev shell — $(python --version)"
            echo "run:  python generate_cards.py --placeholder      # preview, no API calls"
            echo "      python generate_cards.py --groups simple     # real cards, easy deck"
          '';
        };
      });

      # The Python interpreter (with deps) as a buildable package, e.g. for CI.
      packages = forAllSystems (pkgs: {
        default = pythonEnvFor pkgs;
      });

      formatter = forAllSystems (pkgs: pkgs.nixpkgs-fmt);
    };
}
