using System.Text.Json;
using System.Text.Json.Serialization;
using YoutubeExplode;
using YoutubeExplode.Common;
using YoutubeExplode.Playlists;
using YoutubeExplode.Videos.Streams;

var options = new JsonSerializerOptions
{
    PropertyNamingPolicy = JsonNamingPolicy.CamelCase,
    DefaultIgnoreCondition = JsonIgnoreCondition.WhenWritingNull,
    WriteIndented = false
};

try
{
    if (args.Length == 0)
    {
        throw new ArgumentException("Missing command. Use 'inspect' or 'download-audio'.");
    }

    var command = args[0];
    var parsedArgs = ParseArgs(args.Skip(1).ToArray());
    using var youtube = new YoutubeClient();

    object result = command switch
    {
        "inspect" => await InspectAsync(youtube, Required(parsedArgs, "url")),
        "download-audio" => await DownloadAudioAsync(
            youtube,
            Required(parsedArgs, "url"),
            Required(parsedArgs, "output-dir"),
            Required(parsedArgs, "basename")
        ),
        _ => throw new ArgumentException($"Unknown command: {command}")
    };

    Console.WriteLine(JsonSerializer.Serialize(result, options));
    return 0;
}
catch (Exception ex)
{
    Console.Error.WriteLine(JsonSerializer.Serialize(new ErrorDto(ex.GetType().Name, ex.Message), options));
    return 1;
}

static async Task<ManifestDto> InspectAsync(YoutubeClient youtube, string url)
{
    if (LooksLikePlaylist(url))
    {
        return await InspectPlaylistAsync(youtube, url);
    }

    return await InspectVideoAsync(youtube, url);
}

static async Task<ManifestDto> InspectVideoAsync(YoutubeClient youtube, string url)
{
    var video = await youtube.Videos.GetAsync(url);
    var item = VideoDto.FromVideo(video, null);
    var source = new SourceDto(
        Kind: "video",
        Id: item.Id,
        Url: item.Url,
        Title: item.Title,
        Channel: item.Channel,
        PlaylistId: null,
        VideoCount: 1
    );
    return new ManifestDto("video", source, [item]);
}

static async Task<ManifestDto> InspectPlaylistAsync(YoutubeClient youtube, string url)
{
    var playlist = await youtube.Playlists.GetAsync(url);
    var videos = new List<VideoDto>();

    await foreach (var video in youtube.Playlists.GetVideosAsync(url))
    {
        videos.Add(VideoDto.FromPlaylistVideo(video));
    }

    var source = new SourceDto(
        Kind: "playlist",
        Id: playlist.Id.ToString(),
        Url: $"https://www.youtube.com/playlist?list={playlist.Id}",
        Title: playlist.Title,
        Channel: playlist.Author?.ChannelTitle,
        PlaylistId: playlist.Id.ToString(),
        VideoCount: videos.Count
    );
    return new ManifestDto("playlist", source, videos);
}

static async Task<AudioDto> DownloadAudioAsync(
    YoutubeClient youtube,
    string url,
    string outputDir,
    string basename
)
{
    Directory.CreateDirectory(outputDir);
    var manifest = await youtube.Videos.Streams.GetManifestAsync(url);
    var streamInfo = manifest.GetAudioOnlyStreams().GetWithHighestBitrate();
    if (streamInfo is null)
    {
        throw new InvalidOperationException("No audio-only stream is available for this video.");
    }

    var extension = streamInfo.Container.Name.Equals("mp4", StringComparison.OrdinalIgnoreCase)
        ? "m4a"
        : streamInfo.Container.Name;
    var outputPath = Path.Combine(outputDir, $"{basename}.{extension}");
    await youtube.Videos.Streams.DownloadAsync(streamInfo, outputPath);
    return new AudioDto(
        AudioPath: Path.GetFullPath(outputPath),
        Container: streamInfo.Container.Name,
        Bitrate: streamInfo.Bitrate.ToString()
    );
}

static bool LooksLikePlaylist(string url)
{
    var uri = new Uri(url);
    if (uri.AbsolutePath.Contains("playlist", StringComparison.OrdinalIgnoreCase))
    {
        return true;
    }
    return QueryContainsKey(uri.Query, "list");
}

static bool QueryContainsKey(string query, string expectedKey)
{
    var trimmed = query.TrimStart('?');
    foreach (var pair in trimmed.Split('&', StringSplitOptions.RemoveEmptyEntries))
    {
        var key = pair.Split('=', 2)[0];
        if (Uri.UnescapeDataString(key).Equals(expectedKey, StringComparison.OrdinalIgnoreCase))
        {
            return true;
        }
    }
    return false;
}

static Dictionary<string, string> ParseArgs(string[] args)
{
    var result = new Dictionary<string, string>(StringComparer.OrdinalIgnoreCase);
    for (var i = 0; i < args.Length; i++)
    {
        var key = args[i];
        if (!key.StartsWith("--", StringComparison.Ordinal))
        {
            throw new ArgumentException($"Unexpected argument: {key}");
        }
        if (i + 1 >= args.Length)
        {
            throw new ArgumentException($"Missing value for {key}");
        }
        result[key[2..]] = args[++i];
    }
    return result;
}

static string Required(Dictionary<string, string> args, string key)
{
    if (!args.TryGetValue(key, out var value) || string.IsNullOrWhiteSpace(value))
    {
        throw new ArgumentException($"Missing required argument --{key}");
    }
    return value;
}

public sealed record ErrorDto(string Type, string Message);

public sealed record ManifestDto(string Kind, SourceDto Source, IReadOnlyList<VideoDto> Videos);

public sealed record SourceDto(
    string Kind,
    string Id,
    string Url,
    string Title,
    string? Channel,
    string? PlaylistId,
    int VideoCount
);

public sealed record VideoDto(
    string Id,
    string Url,
    string Title,
    string? Channel,
    double? DurationSec,
    string? PlaylistId
)
{
    public static VideoDto FromVideo(YoutubeExplode.Videos.Video video, string? playlistId)
    {
        return new VideoDto(
            Id: video.Id.ToString(),
            Url: $"https://www.youtube.com/watch?v={video.Id}",
            Title: video.Title,
            Channel: video.Author.ChannelTitle,
            DurationSec: video.Duration?.TotalSeconds,
            PlaylistId: playlistId
        );
    }

    public static VideoDto FromPlaylistVideo(PlaylistVideo video)
    {
        return new VideoDto(
            Id: video.Id.ToString(),
            Url: video.Url,
            Title: video.Title,
            Channel: video.Author.ChannelTitle,
            DurationSec: video.Duration?.TotalSeconds,
            PlaylistId: video.PlaylistId.ToString()
        );
    }
}

public sealed record AudioDto(string AudioPath, string Container, string? Bitrate);
