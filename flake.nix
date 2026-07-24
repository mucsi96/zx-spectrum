{
  description = "ZX Spectrum Next kiosk: ZEsarUX patched for NextBASIC host-disk LOAD/SAVE";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-25.05";

    # ZEsarUX master, pinned to the commit the patch was cut against
    zesarux-src = {
      url = "github:chernandezba/zesarux/7d33f6bac01612d9b3c6619ffb85a325bf595198";
      flake = false;
    };
  };

  outputs = { self, nixpkgs, zesarux-src }:
    let
      systems = [ "x86_64-linux" "aarch64-linux" ];
      forAll = f: nixpkgs.lib.genAttrs systems (system: f nixpkgs.legacyPackages.${system});
    in
    {
      packages = forAll (pkgs: rec {
        zesarux-next = pkgs.stdenv.mkDerivation {
          pname = "zesarux-next";
          version = "13.1-SN-nextbasic-hostdisk";

          src = zesarux-src;
          sourceRoot = "source/src";

          patches = [
            ./zesarux-nextbasic-hostdisk.patch
            ./zesarux-nextbasic-highlight.patch
          ];
          patchFlags = [ "-p2" ]; # we are inside src/, diff paths are src/...

          nativeBuildInputs = [ pkgs.pkg-config ];
          buildInputs = with pkgs; [
            SDL2
            xorg.libX11
            xorg.libXext
            ncurses
            alsa-lib
            libpulseaudio
          ];

          # the scripts use "#!/usr/bin/env bash", which does not exist in
          # the Nix build sandbox
          postPatch = ''
            patchShebangs .
          '';

          # ZEsarUX ships its own (non-autotools) configure script
          configurePhase = ''
            runHook preConfigure
            ./configure --prefix $out --enable-sdl2 \
              --disable-caca --disable-aa --disable-fbdev
            runHook postConfigure
          '';

          enableParallelBuilding = true;

          # "make install" generates install.sh at build time (again with an
          # env shebang), so run the two steps explicitly through bash
          installPhase = ''
            runHook preInstall
            bash ./generate_install_sh.sh
            bash ./install.sh
            runHook postInstall
          '';

          meta = {
            description = "ZEsarUX with NextBASIC host-disk LOAD/SAVE patch (ZX Spectrum Next)";
            homepage = "https://github.com/chernandezba/zesarux";
            license = pkgs.lib.licenses.gpl3Plus;
            mainProgram = "zesarux";
          };
        };

        # `nix run` / `nix run .#spectrum [-- program]` — boots NextZXOS with the
        # repo's programs available as host .bas files. Works on WSL2 (WSLg).
        spectrum = pkgs.writeShellApplication {
          name = "spectrum";
          runtimeInputs = [ zesarux-next ];
          text = ''
            data="''${XDG_DATA_HOME:-$HOME/.local/share}/zx-spectrum-next"
            mkdir -p "$data/programs"

            # Private writable copy of the NextZXOS SD image
            if [ ! -f "$data/tbblue.mmc" ]; then
              cp --no-preserve=mode "${zesarux-next}/share/zesarux/tbblue.mmc" "$data/tbblue.mmc"
            fi

            # Seed missing programs from the repo listings. Host .bas files
            # are plain text listings; never overwrite saved work.
            if [ -d programs ]; then
              for src in programs/*.bas; do
                [ -e "$src" ] || continue
                dst="$data/programs/$(basename "$src")"
                [ -e "$dst" ] || cp "$src" "$dst"
              done
            fi

            export ZESARUX_NEXTBASIC_DIR="$data/programs"
            export ZESARUX_NEXTBASIC_HIGHLIGHT=1
            if [ $# -ge 1 ]; then
              export ZESARUX_NEXTBASIC_AUTOLOAD="$1"
            fi

            exec zesarux --machine tbblue --enable-mmc --enable-divmmc-ports \
              --mmc-file "$data/tbblue.mmc" \
              --nowelcomemessage --quickexit --hidemousepointer \
              --stats-disable-check-updates --stats-disable-check-yesterday-users \
              --stats-send-already-asked --tbblue-autoconfigure-sd-already-asked \
              --def-f-function F10 ExitEmulator
          '';
        };

        # `nix run .#menu` — the kiosk program-picker menu, like on the Pi.
        # Uses the same state directory as the `spectrum` runner.
        menu = pkgs.writeShellApplication {
          name = "spectrum-menu";
          runtimeInputs = [ zesarux-next pkgs.dialog pkgs.ncurses ];
          text = ''
            data="''${XDG_DATA_HOME:-$HOME/.local/share}/zx-spectrum-next"
            mkdir -p "$data/programs"
            if [ -d programs ]; then
              for src in programs/*.bas; do
                [ -e "$src" ] || continue
                dst="$data/programs/$(basename "$src")"
                [ -e "$dst" ] || cp "$src" "$dst"
              done
            fi
            export SPECTRUM_PROGRAMS="$data/programs"
            export SPECTRUM_MMC="$data/tbblue.mmc"
            export ZESARUX="${zesarux-next}/bin/zesarux"
            exec bash ${./spectrum-launcher.sh}
          '';
        };

        default = spectrum;
      });

      apps = forAll (pkgs: rec {
        spectrum = {
          type = "app";
          program = "${self.packages.${pkgs.system}.spectrum}/bin/spectrum";
        };
        menu = {
          type = "app";
          program = "${self.packages.${pkgs.system}.menu}/bin/spectrum-menu";
        };
        default = spectrum;
      });

      devShells = forAll (pkgs: {
        default = pkgs.mkShell {
          packages = with pkgs; [
            python3
            dialog
            ansible
            # for hacking on the ZEsarUX patch itself:
            pkg-config
            SDL2
            xorg.libX11
            xorg.libXext
            ncurses
            alsa-lib
            libpulseaudio
          ];
          shellHook = ''
            echo "ZX Spectrum Next dev shell"
            echo "  nix run .#spectrum            boot NextZXOS (menu)"
            echo "  nix run .#spectrum -- NAME    boot straight into programs/NAME.bas"
          '';
        };
      });
    };
}
