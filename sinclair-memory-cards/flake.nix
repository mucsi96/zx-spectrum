{
  description = "Sinclair BASIC memory-card PDF generator (Python)";

  inputs.nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";

  outputs = { self, nixpkgs }:
    let
      systems = [ "x86_64-linux" "aarch64-linux" "x86_64-darwin" "aarch64-darwin" ];
      forAllSystems = f:
        nixpkgs.lib.genAttrs systems (system: f nixpkgs.legacyPackages.${system});

      # Single source of truth: read the dependency names from requirements.txt,
      # strip version specifiers/comments, and resolve each against python3Packages.
      pythonEnvFor = pkgs:
        let
          lines = pkgs.lib.splitString "\n" (builtins.readFile ./requirements.txt);
          nameOf = line:
            let m = builtins.match "[[:space:]]*([A-Za-z0-9][A-Za-z0-9._-]*).*" line;
            in if m == null then null else builtins.head m;
          names = builtins.filter (n: n != null) (map nameOf lines);
          deps = map (n: pkgs.python3Packages.${n}) names;
        in
        pkgs.python3.withPackages (_: deps);
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
